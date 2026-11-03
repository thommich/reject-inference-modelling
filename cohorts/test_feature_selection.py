"""AWS-free regression tests for the feature-selection flow."""
import importlib
import io
import json
import os
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
TEST_DEPS = Path(os.environ.get("FS_TEST_DEPS", ROOT / ".deps"))
sys.path.insert(0, str(TEST_DEPS)) if TEST_DEPS.exists() else None
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import fs_orchestrator as orch


class MemoryS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Bucket, Key, Body, **kwargs):
        self.objects[(Bucket, Key)] = Body if isinstance(Body, bytes) else Body.encode()

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


class FakeSession:
    def upload_data(self, **kwargs):
        return "s3://bucket/code/fs_processor.py"


class FakeSM:
    def __init__(self, mode="success"):
        self.active = {}
        self.peak = 0
        self.submissions = 0
        self.mode = mode
        self.failed_once = set()

    def describe_processing_job(self, *, ProcessingJobName):
        spec = self.active.pop(ProcessingJobName)
        if self.mode == "oom" and spec["batch_index"] == "0" and "0" not in self.failed_once:
            self.failed_once.add("0")
            return {"ProcessingJobStatus": "Failed", "FailureReason": "Out of memory"}
        return {"ProcessingJobStatus": "Completed"}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.s3 = MemoryS3()
        self.sm = FakeSM()
        self.session = FakeSession()

    def test_allocation_capped_and_exact(self):
        strata = pd.DataFrame({"total_estrato": [1, 2, 7]})
        allocation = orch._allocate_strata(strata, 9)
        self.assertEqual(sum(allocation), 9)
        self.assertTrue(all(x <= y for x, y in zip(allocation, [1, 2, 7])))
        with self.assertRaises(ValueError):
            orch._allocate_strata(strata, 11)

    def test_run_scoped_sample_keeps_vintage_and_null_strata(self):
        class Athena:
            def __init__(self):
                self.executed = []
            def query(self, sql):
                if "total_estrato" in sql:
                    return pd.DataFrame({"produto_final_consolidado": ["CP", None],
                                         "bancos": ["A", "B"], "spi": ["S", "N"],
                                         "faixa_idade": ["1", "2"],
                                         "total_estrato": [7, 3]})
                if "HAVING COUNT(*) > 1" in sql:
                    return pd.DataFrame()
                if "COUNT(*)" in sql:
                    return pd.DataFrame({"n": [10 if "tmp_amostra_fs_ids" in sql and "WHERE" not in sql else 0]})
                raise AssertionError(sql)
            def execute(self, sql):
                self.executed.append(sql)
        athena = Athena()
        sample, count = orch.prepare_sample(athena, "workspace_db.base",
                                            "20261102t010203_abcd", 10)
        self.assertEqual(count, 10)
        self.assertIn("20261102t010203_abcd", sample)
        self.assertIn('r."safra"', athena.executed[-1])
        self.assertIn("IS NOT DISTINCT FROM", athena.executed[-1])

    def test_plan_splits_columns_and_selects_cheapest_fit(self):
        config = orch.default_config("bucket")
        config["max_corr_columns"] = 3
        info = {"group": "MLTools", "table": "workspace_db.book", "join_key": "pk_riznumdoc_xx"}
        cols = [{"source": "f", "name": f"x{i}"} for i in range(7)]
        tasks = orch.plan_book("20261102t010203_abcd", "BC", info, config,
                               "workspace_db.sample", 1000, 100, cols)
        self.assertEqual([len(t["feature_columns"]) for t in tasks], [3, 3, 1])
        self.assertEqual([t["instance_type"] for t in tasks], ["ml.r5.4xlarge"] * 3)
        self.assertEqual(tasks[0]["batch_count"], 3)

    def test_catalog_excludes_unpriced_types(self):
        self.assertEqual(len(orch.INSTANCE_TIERS), 71)
        self.assertEqual(sum(v["usd_per_hour"] is None for v in orch.INSTANCE_CATALOG.values()), 3)
        self.assertNotIn("ml.m5.16xlarge", orch.eligible_instances(10))

    def test_duplicate_book_key_fails_preflight(self):
        class Athena:
            def query(self, sql):
                return pd.DataFrame({"key": ["duplicate"]})
        with self.assertRaisesRegex(ValueError, "not unique"):
            orch._check_book_join(Athena(), "workspace_db.base", "workspace_db.sample",
                                  "workspace_db.book", "pk_riznumdoc_xx", 100)

    def _manifest(self, count=12, columns=1):
        config = orch.default_config("bucket")
        config["poll_interval"] = 0
        manifest = {"run_id": "20261102t010203_abcd", "sample_table": "workspace_db.sample",
                    "sample_count": 100, "config": config, "tasks": {}, "books": {}, "code_uri": None}
        for i in range(count):
            book = f"B{i}"
            info = {"group": "MLTools", "table": "workspace_db.book", "join_key": "pk_riznumdoc_xx"}
            cols = [{"source": "f", "name": f"x{j}"} for j in range(columns)]
            spec = orch._task_spec(manifest["run_id"], book, info, config,
                                   manifest["sample_table"], cols, "0", 100, 100,
                                   "ml.r5.4xlarge")
            spec["batch_count"] = 1
            task_id = book.lower() + "_b0"
            orch._add_task(self.s3, "bucket", manifest, task_id, spec)
            manifest["books"][book] = {**info, "status": "pending", "task_ids": [task_id]}
        return manifest

    def _install_sagemaker_mock(self, quota_first=False):
        sm, s3 = self.sm, self.s3
        class FakeProcessor:
            def __init__(self, **kwargs):
                self.instance_type = kwargs["instance_type"]
            def run(self, **kwargs):
                if quota_first and self.instance_type == "ml.r5.4xlarge":
                    raise RuntimeError("ResourceLimitExceeded")
                spec = orch._get_json(s3, kwargs["arguments"][1])
                sm.submissions += 1
                sm.active[kwargs["job_name"]] = spec
                sm.peak = max(sm.peak, len(sm.active))
                prefix = kwargs["outputs"][0]["destination"]
                identity = {key: spec[key] for key in ("run_id", "book", "batch_index", "feature_hash")}
                orch._put_json(s3, prefix + "resumo.json", {**identity, "status": "ok"})
                identity_header = "run_id,book,batch_index,feature_hash"
                identity_values = ",".join(str(identity[key]) for key in
                                           ("run_id", "book", "batch_index", "feature_hash"))
                for name, payload in {
                    "variaveis_excluidas.csv": f"{identity_header},variavel,etapa\n",
                    "metricas.csv": f"{identity_header},etapa,n_samples\n",
                    "variaveis_por_segmento.csv": f"{identity_header},nivel,variavel\n",
                    "variaveis_finais.csv": (f"{identity_header},variavel,tipo\n"
                                             f"{identity_values},{spec['feature_columns'][0]['name']},selecionada\n"),
                }.items():
                    bucket, key = orch._s3_parts(prefix + name)
                    s3.put_object(Bucket=bucket, Key=key, Body=payload)
        processing = types.ModuleType("sagemaker.processing")
        processing.ProcessingOutput = lambda **kwargs: kwargs
        sklearn_processing = types.ModuleType("sagemaker.sklearn.processing")
        sklearn_processing.SKLearnProcessor = FakeProcessor
        self.old_modules = {key: sys.modules.get(key) for key in
                            ("sagemaker", "sagemaker.processing", "sagemaker.sklearn", "sagemaker.sklearn.processing")}
        for name, module in {
            "sagemaker": types.ModuleType("sagemaker"),
            "sagemaker.processing": processing,
            "sagemaker.sklearn": types.ModuleType("sagemaker.sklearn"),
            "sagemaker.sklearn.processing": sklearn_processing,
        }.items():
            sys.modules[name] = module
        self.addCleanup(self._restore_modules)

    def _restore_modules(self):
        for name, original in self.old_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_twelve_jobs_cap_and_run_scoped_consolidation(self):
        self._install_sagemaker_mock()
        manifest = self._manifest()
        old_sleep = orch.time.sleep
        orch.time.sleep = lambda _: None
        self.addCleanup(setattr, orch.time, "sleep", old_sleep)
        orch.run_jobs(manifest, s3=self.s3, sm=self.sm, bucket="bucket", role="role",
                      session=self.session, network_config=None,
                      code_path=str(ROOT / "fs_processor.py"))
        self.assertEqual(self.sm.peak, 10)
        self.assertTrue(all(v["status"] == "succeeded" for v in manifest["books"].values()))
        with TemporaryDirectory() as folder:
            summary = orch.consolidate(manifest, self.s3, "bucket", folder)
            self.assertEqual(summary["selected_feature_rows"], 12)
            self.assertTrue((Path(folder) / "variaveis_finais.csv").is_file())

    def test_smaller_concurrency_limit(self):
        self._install_sagemaker_mock()
        manifest = self._manifest(count=7)
        manifest["config"]["max_concurrent"] = 3
        old_sleep = orch.time.sleep
        orch.time.sleep = lambda _: None
        self.addCleanup(setattr, orch.time, "sleep", old_sleep)
        orch.run_jobs(manifest, s3=self.s3, sm=self.sm, bucket="bucket", role="role",
                      session=self.session, network_config=None,
                      code_path=str(ROOT / "fs_processor.py"))
        self.assertEqual(self.sm.peak, 3)

    def test_resume_polls_existing_job_without_resubmission(self):
        self._install_sagemaker_mock()
        manifest = self._manifest(count=1)
        manifest["code_uri"] = "s3://bucket/code/fs_processor.py"
        orch._submit_one(manifest, "b0_b0", s3=self.s3, sm=self.sm, bucket="bucket",
                         role="role", session=self.session, network_config=None)
        self.assertEqual(self.sm.submissions, 1)
        old_sleep = orch.time.sleep
        orch.time.sleep = lambda _: None
        self.addCleanup(setattr, orch.time, "sleep", old_sleep)
        resumed = orch._get_json(self.s3, orch._manifest_uri("bucket", manifest["run_id"]))
        orch.run_jobs(resumed, s3=self.s3, sm=self.sm, bucket="bucket", role="role",
                      session=self.session, network_config=None,
                      code_path=str(ROOT / "fs_processor.py"))
        self.assertEqual(self.sm.submissions, 1)
        self.assertEqual(resumed["books"]["B0"]["status"], "succeeded")

    def test_quota_tries_another_priced_type(self):
        self._install_sagemaker_mock(quota_first=True)
        manifest = self._manifest(count=1)
        old_sleep = orch.time.sleep
        orch.time.sleep = lambda _: None
        self.addCleanup(setattr, orch.time, "sleep", old_sleep)
        orch.run_jobs(manifest, s3=self.s3, sm=self.sm, bucket="bucket", role="role",
                      session=self.session, network_config=None,
                      code_path=str(ROOT / "fs_processor.py"))
        task = next(iter(manifest["tasks"].values()))
        self.assertEqual(task["status"], "succeeded")
        self.assertNotEqual(task["spec"]["instance_type"], "ml.r5.4xlarge")

    def test_oom_splits_and_recovers(self):
        self._install_sagemaker_mock()
        self.sm.mode = "oom"
        manifest = self._manifest(count=1, columns=4)
        old_sleep = orch.time.sleep
        orch.time.sleep = lambda _: None
        self.addCleanup(setattr, orch.time, "sleep", old_sleep)
        orch.run_jobs(manifest, s3=self.s3, sm=self.sm, bucket="bucket", role="role",
                      session=self.session, network_config=None,
                      code_path=str(ROOT / "fs_processor.py"))
        self.assertEqual(manifest["tasks"]["b0_b0"]["status"], "superseded")
        self.assertEqual(manifest["books"]["B0"]["status"], "succeeded")
        self.assertEqual(len([t for t in manifest["tasks"].values() if t["status"] == "succeeded"]), 2)


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.metadata
        cls.old_version = importlib.metadata.version
        pins = {"awswrangler": "3.5.2", "feature-engine": "1.6.2", "scipy": "1.10.1"}
        importlib.metadata.version = lambda name: pins[name] if name in pins else cls.old_version(name)
        cls.old_boto3 = sys.modules.get("boto3")
        cls.old_wr = sys.modules.get("awswrangler")
        sys.modules["boto3"] = types.ModuleType("boto3")
        sys.modules["awswrangler"] = types.ModuleType("awswrangler")
        try:
            cls.worker = importlib.import_module("fs_processor")
        finally:
            importlib.metadata.version = cls.old_version

    @classmethod
    def tearDownClass(cls):
        for name, original in (("boto3", cls.old_boto3), ("awswrangler", cls.old_wr)):
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def _spec(self):
        features = [{"source": "f", "name": f"f{i}"} for i in range(1, 6)]
        return {"run_id": "run123", "book": "BC", "batch_index": "0",
                "feature_columns": features, "feature_hash": orch._spec_hash(features),
                "base_table": "workspace_db.base", "feature_table": "workspace_db.book",
                "sample_table": "workspace_db.sample", "join_key": "pk_riznumdoc_xx",
                "target": "target", "segments": [], "database": "workspace_db",
                "workgroup": "wg", "athena_output": "s3://bucket/athena/",
                "profile_rows": 250, "drop_missing": 0.05,
                "corr_threshold": 0.8, "agg_method": "union", "min_samples": 100}

    def test_worker_query_projects_only_batch_columns(self):
        spec = self._spec()
        spec["feature_columns"] = spec["feature_columns"][:1]
        query = self.worker.build_query(spec)
        self.assertIn('f."f1"', query)
        self.assertNotIn('f."f2"', query)
        self.assertIn('b."safra" = a."safra"', query)
        self.assertNotIn("b.*", query)

    def test_worker_filters_and_writes_provenance(self):
        n = 250
        rng = np.random.default_rng(10)
        f1 = np.arange(n, dtype=float)
        f4 = np.full(n, np.nan)
        f4[0] = 1.0
        frame = pd.DataFrame({"target": rng.integers(0, 2, n), "f1": f1,
                              "f2": f1.copy(), "f3": np.ones(n), "f4": f4,
                              "f5": rng.normal(size=n)})
        spec = self._spec()
        original = self.worker.carrega_tabela
        self.worker.carrega_tabela = lambda _: frame.copy()
        try:
            with TemporaryDirectory() as folder:
                result = self.worker.run_task(spec, Path(folder))
                self.assertEqual(set(result["selected"]), {"f1", "f5"})
                summary = json.loads((Path(folder) / "resumo.json").read_text())
                self.assertEqual(summary["features_iniciais"], 5)
                self.assertEqual(summary["n_samples"], n)
                excluded = pd.read_csv(Path(folder) / "variaveis_excluidas.csv")
                self.assertEqual(set(excluded["variavel"]), {"f2", "f3", "f4"})
                self.assertEqual(set(excluded["run_id"]), {"run123"})
        finally:
            self.worker.carrega_tabela = original

    def test_null_segment_is_processed(self):
        n = 250
        frame = pd.DataFrame({"target": np.arange(n) % 2,
                              "segment": [None] * 125 + ["A"] * 125,
                              "feature": np.arange(n, dtype=float)})
        selected, _, metrics, _ = self.worker.limpeza_variaveis_hierarquica_final(
            frame, "target", ["feature"], "BC", 0.05,
            segments=["segment"], min_samples_per_segment=100,
            aggregation_method="union")
        self.assertEqual(selected, ["feature"])
        self.assertEqual(len(metrics.loc[metrics["etapa"] == "final"]), 2)


if __name__ == "__main__":
    unittest.main()
