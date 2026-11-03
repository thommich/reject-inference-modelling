# SageMaker feature selection

This package runs the first-stage feature selection for the configured 11 MLTools, 14 Thoth, and 17 Customizados books. The Scikit-learn Processing image remains **`1.2-1`**, as required for the deployment environment.

## Run in Studio

Place `03.1.Feature selection.ipynb`, `fs_orchestrator.py`, and `fs_processor.py` in the same Studio directory. Run the notebook's two code cells. It gets the role, bucket, subnet, and security group from the existing `GlobalInfoStudio` module and uses the existing `MLTools.Connections.Athena` wrapper. The default Athena workgroup is `analytics-workgroup`; set `FS_ATHENA_WORKGROUP` and `FS_ATHENA_OUTPUT` in Studio if needed.

The first run creates `workspace_db.tmp_amostra_fs_aloc_<run_id>` and `workspace_db.tmp_amostra_fs_ids_<run_id>`, then writes task specs and `manifest.json` under `s3://<bucket>/fs-results/<run_id>/`. It submits at most 10 Processing Jobs at once. Each worker reads only its batch's feature columns. Results are consolidated under `feature_selection_saidas/<run_id>/` in Studio, and the run summary is also written to S3.

To resume after a kernel restart, set `FS_RESUME_RUN_ID` to the ID in the S3 manifest and rerun the notebook. Keep the same configuration. The existing sample and submitted job names are reused.

## Policies and limits

- The sample uses `(pk_riznumdoc_xx, safra)` and includes null-valued strata. A book fails preflight if its feature-side join key is nonunique for sampled people or if joined row count differs from the sample count.
- Candidate features are numeric Glue columns from the base and book tables, excluding the configured metadata and target/segment fields. Nonnumeric candidates are reported in the manifest. Colliding feature names fail preflight.
- Batches contain at most 1,024 feature columns and must fit the conservative estimate within 60% of advertised RAM. The selected instance is the lowest hourly-priced fit from the 71-type allowlist. Three types with no `sa-east-1` Processing rate are not scheduled.
- Filtering remains: more than 95% missing; at least 95% constant; exact duplicates; absolute Spearman correlation at least 0.8; four nested segment levels, minimum 100 rows per leaf, union aggregation. Correlation between features in different batches is **not checked**.
- The worker pins `awswrangler==3.5.2`, `feature-engine==1.6.2`, and `scipy==1.10.1` when a different version or no version is installed. The Processing subnet needs a usable package source, or these exact packages must already be installed in the target environment.

## Account checks before a real run

Verify the Studio SageMaker Python SDK exposes `sagemaker.sklearn.processing.SKLearnProcessor` for image `1.2-1`; the archived environment's image choice has been retained. Check role access to SageMaker Processing, Glue, Athena, S3, and ECR; base and book schemas; Athena workgroup/output path; per-type Processing quotas and regional capacity; subnet IPs and routes; and worker access to dependencies. The public price catalog does not prove account-specific quota or capacity.

## Local simulation

The included `test_feature_selection.py` uses mocked AWS calls and synthetic data. On Python 3.10, install `requirements_simulation.txt` and run `python test_feature_selection.py`. It checks sample allocation and SQL shape, per-batch planning, the 10-job cap, quota fallback, OOM splitting, output consolidation, and the worker filters. No real AWS call or target-environment memory measurement was performed.
