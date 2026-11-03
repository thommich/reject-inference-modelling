"""Execute one planned feature-selection batch in SageMaker Processing.

The worker retains the existing four-level filter policy. Its input is a task spec
created by fs_orchestrator; only the columns named in that spec are queried.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_PINNED_DEPS = (("awswrangler", "awswrangler", "3.5.2"),
                ("feature-engine", "feature_engine", "1.6.2"),
                ("scipy", "scipy", "1.10.1"))
for _package, _module, _version in _PINNED_DEPS:
    try:
        _installed = importlib.metadata.version(_package)
    except importlib.metadata.PackageNotFoundError:
        _installed = None
    if _installed != _version:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                               f"{_package}=={_version}"])
        importlib.invalidate_caches()

import boto3
import numpy as np
import pandas as pd
import awswrangler as wr
from scipy.stats import rankdata
from feature_engine.selection import DropConstantFeatures, DropDuplicateFeatures

_DEFAULT_SEGMENTS = ["produto_final_consolidado", "bancos", "spi", "faixa_idade"]
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _table_sql(name: str) -> str:
    parts = name.split(".")
    if len(parts) != 2 or not all(_IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(f"Invalid qualified table name: {name!r}")
    return ".".join(f'"{part}"' for part in parts)


def _column_sql(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise ValueError(f"Invalid column name: {name!r}")
    return f'"{name}"'


def _load_spec(uri: str) -> dict:
    if uri.startswith("s3://"):
        bucket, key = uri[5:].split("/", 1)
        payload = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
        spec = json.loads(payload)
    else:
        spec = json.loads(Path(uri).read_text(encoding="utf-8"))
    required = ["run_id", "book", "batch_index", "feature_columns", "feature_hash",
                "base_table", "feature_table", "sample_table", "join_key", "target",
                "segments", "database", "workgroup", "athena_output"]
    missing = [name for name in required if name not in spec]
    if missing:
        raise ValueError(f"Missing task-spec fields: {missing}")
    columns = spec["feature_columns"]
    if not isinstance(columns, list) or len(columns) != len({c.get("name") for c in columns}):
        raise ValueError("feature_columns must have unique names")
    for column in columns:
        if column.get("source") not in ("b", "f"):
            raise ValueError(f"Invalid feature source: {column!r}")
        _column_sql(column["name"])
    digest = hashlib.sha256(json.dumps(columns, sort_keys=True).encode()).hexdigest()
    if digest != spec["feature_hash"]:
        raise ValueError("Feature-list hash mismatch")
    return spec


def build_query(spec: dict) -> str:
    """Project only this task's shared columns and numeric feature batch."""
    base = _table_sql(spec["base_table"])
    feature = _table_sql(spec["feature_table"])
    sample = _table_sql(spec["sample_table"])
    join_key = _column_sql(spec["join_key"])
    shared = list(dict.fromkeys(["pk_riznumdoc_xx", "safra", spec["target"], *spec["segments"]]))
    feature_names = {column["name"] for column in spec["feature_columns"]}
    overlap = feature_names.intersection(shared)
    if overlap:
        raise ValueError(f"Feature/shared-column collision: {sorted(overlap)}")
    select = [f'b.{_column_sql(name)} AS {_column_sql(name)}' for name in shared]
    select += [f'{column["source"]}.{_column_sql(column["name"])} AS {_column_sql(column["name"])}'
               for column in spec["feature_columns"]]
    pk = _column_sql("pk_riznumdoc_xx")
    vintage = _column_sql("safra")
    return ("SELECT " + ", ".join(select) + "\n"
            + f"FROM {sample} a JOIN {base} b ON b.{pk} = a.{pk} "
            + f"AND b.{vintage} = a.{vintage}\n"
            + f"LEFT JOIN {feature} f ON b.{join_key} = f.{join_key}")


def carrega_tabela(spec: dict) -> pd.DataFrame:
    database = spec["database"]
    if not _IDENTIFIER.fullmatch(database):
        raise ValueError(f"Invalid database: {database!r}")
    return wr.athena.read_sql_query(
        build_query(spec), database=database, ctas_approach=False,
        workgroup=spec["workgroup"], s3_output=spec["athena_output"],
        boto3_session=boto3.Session(region_name=spec.get("region", "sa-east-1")),
    )


def limpeza_variaveis_otimizada_final(
    df_train: pd.DataFrame, target: str, features: List[str], drop_missing: float,
    drop_constant: Optional[Any] = None,
    drop_duplicate: Optional[Any] = None,
    drop_correlated_threshold: float = 0.8,
    drop_correlated_method: str = "variance",
    correlation_method: str = "spearman",
) -> Tuple[List[str], Dict[str, List[str]], Dict[str, Any]]:
    """Pipeline: missing, constante, duplicada, correlacionada."""
    if drop_constant is None:
        drop_constant = DropConstantFeatures(tol=0.95)
    if drop_duplicate is None:
        drop_duplicate = DropDuplicateFeatures()

    metrics: Dict[str, Any] = {"inicial": len(features)}
    excluded_vars: Dict[str, List[str]] = {}
    df_features = df_train[features]
    missing_pct = df_features.isna().sum() / len(df_features)
    current_features = missing_pct[missing_pct <= (1 - drop_missing)].index.tolist()
    removed = sorted(set(features) - set(current_features))
    metrics["missing"] = {"antes": len(features), "removidas": len(removed), "depois": len(current_features)}
    excluded_vars["missing"] = removed
    print(f"[missing > {1-drop_missing:.2f}] antes={len(features)} | removidas={len(removed)} | depois={len(current_features)}")
    if not current_features:
        metrics["final"] = 0
        return [], excluded_vars, metrics

    y = df_train[target]
    x_curr = df_train[current_features].fillna(-9999999)
    before_vars = current_features.copy()
    drop_constant.fit(x_curr, y)
    current_features = list(drop_constant.get_feature_names_out(input_features=current_features))
    removed = sorted(set(before_vars) - set(current_features))
    metrics["drop_constant"] = {"antes": len(before_vars), "removidas": len(removed), "depois": len(current_features)}
    excluded_vars["drop_constant"] = removed
    print(f"[drop_constant] antes={len(before_vars)} | removidas={len(removed)} | depois={len(current_features)}")
    if not current_features:
        metrics["final"] = 0
        return [], excluded_vars, metrics

    x_curr = df_train[current_features].fillna(-9999999)
    before_vars = current_features.copy()
    if len(current_features) >= 2:
        drop_duplicate.fit(x_curr, y)
        current_features = list(drop_duplicate.get_feature_names_out(input_features=current_features))
    removed = sorted(set(before_vars) - set(current_features))
    metrics["drop_duplicate"] = {"antes": len(before_vars), "removidas": len(removed), "depois": len(current_features)}
    excluded_vars["drop_duplicate"] = removed
    print(f"[drop_duplicate] antes={len(before_vars)} | removidas={len(removed)} | depois={len(current_features)}")
    if not current_features:
        metrics["final"] = 0
        return [], excluded_vars, metrics

    if drop_correlated_threshold is not None and drop_correlated_threshold < 1.0:
        before_vars = current_features.copy()
        x_corr_df = df_train[current_features].copy()
        for col in x_corr_df.columns:
            if x_corr_df[col].isna().any():
                median_val = x_corr_df[col].median()
                fill_value = -9999999 - hash(col) % 1000000 if pd.isna(median_val) else median_val
                x_corr_df[col] = x_corr_df[col].fillna(fill_value)
        x_corr = x_corr_df.values
        n_vars = x_corr.shape[1]
        if drop_correlated_method == "missing values":
            selection_metric = df_train[current_features].isna().sum().values
            keep_higher = False
        else:
            selection_metric = np.var(x_corr, axis=0)
            keep_higher = True

        if correlation_method.lower() == "spearman":
            ranked = np.apply_along_axis(rankdata, 0, x_corr)
            std = ranked.std(axis=0)
            std[std == 0] = 1
            normalized = (ranked - ranked.mean(axis=0)) / std
        else:
            std = x_corr.std(axis=0)
            std[std == 0] = 1
            normalized = (x_corr - x_corr.mean(axis=0)) / std
        corr_matrix = np.atleast_2d(np.corrcoef(normalized.T))
        corr_matrix = np.nan_to_num(corr_matrix)
        correlated_pairs = []
        for i in range(n_vars):
            for j in range(i + 1, n_vars):
                corr_val = abs(corr_matrix[i, j])
                if corr_val >= drop_correlated_threshold:
                    correlated_pairs.append((i, j, corr_val))
        correlated_pairs.sort(key=lambda x: x[2], reverse=True)
        print(f"[drop_correlated] Processando {len(correlated_pairs)} pares correlacionados")
        to_drop = set()
        for idx_i, idx_j, _ in correlated_pairs:
            if idx_i in to_drop or idx_j in to_drop:
                continue
            metric_i, metric_j = selection_metric[idx_i], selection_metric[idx_j]
            if keep_higher:
                to_drop.add(idx_j if metric_i > metric_j else idx_i)
            else:
                to_drop.add(idx_j if metric_i < metric_j else idx_i)
        current_features = [name for i, name in enumerate(current_features) if i not in to_drop]
        removed = sorted(set(before_vars) - set(current_features))
        metrics["drop_correlated"] = {
            "antes": len(before_vars), "removidas": len(removed),
            "depois": len(current_features), "pares_encontrados": len(correlated_pairs),
        }
        excluded_vars["drop_correlated"] = removed
        print(f"[drop_correlated] antes={len(before_vars)} | removidas={len(removed)} | depois={len(current_features)}")

    metrics["final"] = len(current_features)
    print(f"[final] total={metrics['final']}")
    return current_features, excluded_vars, metrics


def _montar_segment_info(segmentos_pai: dict, nome_tabela: str, segments: List[str]) -> dict:
    info = {"tabela": nome_tabela}
    for i, seg in enumerate(segments):
        info[f"segment_level_{i}"] = seg
        info[f"segment_value_{i}"] = segmentos_pai.get(seg, "N/A")
    return info


def _registrar_resultados(
    features_finais: List[str], excluded_vars: dict, metrics: dict, df_train: pd.DataFrame,
    segment_info: dict, nivel: str, excluidas_rows: list, metricas_rows: list,
    variaveis_por_segmento_rows: list,
) -> None:
    for etapa, vars_excluidas in excluded_vars.items():
        for var in vars_excluidas:
            excluidas_rows.append({**segment_info, "etapa": etapa, "variavel": var})
    metricas_rows.append({
        **segment_info, "n_features_inicial": metrics.get("inicial", 0),
        "n_features_final": metrics.get("final", 0), "n_samples": len(df_train), "etapa": "final",
    })
    for etapa in ["missing", "drop_constant", "drop_duplicate", "drop_correlated"]:
        if etapa in metrics:
            metricas_rows.append({
                **segment_info, "n_features_inicial": metrics[etapa].get("antes", 0),
                "n_features_final": metrics[etapa].get("depois", 0),
                "n_samples": len(df_train), "etapa": etapa,
            })
    for var in features_finais:
        variaveis_por_segmento_rows.append({**segment_info, "nivel": nivel, "variavel": var})


def _processar_nivel_segmentacao(
    df_train: pd.DataFrame, target: str, features: List[str], nome_tabela: str,
    drop_missing: float, segments: List[str], nivel_atual: int, segmentos_pai: dict,
    drop_constant: Any, drop_duplicate: Any, drop_correlated_threshold: float,
    drop_correlated_method: str, correlation_method: str,
    min_samples_per_segment: int, aggregation_method: str,
    excluidas_rows: list, metricas_rows: list, variaveis_por_segmento_rows: list,
) -> List[str]:
    if nivel_atual >= len(segments):
        features_finais, excluded_vars, metrics = limpeza_variaveis_otimizada_final(
            df_train, target, features, drop_missing, drop_constant, drop_duplicate,
            drop_correlated_threshold, drop_correlated_method, correlation_method,
        )
        segment_info = _montar_segment_info(segmentos_pai, nome_tabela, segments)
        _registrar_resultados(
            features_finais, excluded_vars, metrics, df_train, segment_info,
            f"level_{nivel_atual}", excluidas_rows, metricas_rows, variaveis_por_segmento_rows,
        )
        return features_finais

    segment_col = segments[nivel_atual]
    segment_values = sorted(df_train[segment_col].unique(), key=str)
    indent = "  " * nivel_atual
    print(f"\n{indent}# NIVEL {nivel_atual}: {segment_col} | Valores: {segment_values}")
    features_por_valor = {}
    for valor in segment_values:
        mask = df_train[segment_col].isna() if pd.isna(valor) else df_train[segment_col] == valor
        df_filtrado = df_train[mask].copy()
        n_samples = len(df_filtrado)
        print(f"{indent}>> {segment_col}={valor}: {n_samples} amostras")
        if n_samples < min_samples_per_segment:
            print(f"{indent}AVISO: Menos de {min_samples_per_segment} amostras. Pulando.")
            continue
        novos_segmentos_pai = {**segmentos_pai, segment_col: valor}
        features_selecionadas = _processar_nivel_segmentacao(
            df_filtrado, target, features, nome_tabela, drop_missing, segments,
            nivel_atual + 1, novos_segmentos_pai, drop_constant, drop_duplicate,
            drop_correlated_threshold, drop_correlated_method, correlation_method,
            min_samples_per_segment, aggregation_method, excluidas_rows, metricas_rows,
            variaveis_por_segmento_rows,
        )
        if features_selecionadas:
            features_por_valor[valor] = features_selecionadas

    valid_features = [f for f in features_por_valor.values() if f]
    if not valid_features:
        return []
    if len(valid_features) == 1:
        features_agregadas = valid_features[0]
    elif aggregation_method == "intersection":
        features_agregadas = sorted(set.intersection(*(set(f) for f in valid_features)))
    else:
        features_agregadas = sorted(set.union(*(set(f) for f in valid_features)))

    segment_info = _montar_segment_info(segmentos_pai, nome_tabela, segments[:nivel_atual])
    for var in features_agregadas:
        row = {
            **segment_info, f"segment_level_{nivel_atual}": segment_col,
            f"segment_value_{nivel_atual}": "AGREGADO",
            "nivel": f"level_{nivel_atual}_agregado", "variavel": var,
        }
        variaveis_por_segmento_rows.append(row)
        if nivel_atual == 0:
            final_row = {"tabela": nome_tabela, "nivel": "final", "variavel": var}
            for i in range(len(segments)):
                final_row[f"segment_level_{i}"] = "N/A"
                final_row[f"segment_value_{i}"] = "FINAL"
            variaveis_por_segmento_rows.append(final_row)
    return features_agregadas


def limpeza_variaveis_hierarquica_final(
    df_train: pd.DataFrame, target: str, features: List[str], nome_tabela: str,
    drop_missing: float, segments: Optional[List[str]] = None,
    drop_constant: Optional[Any] = None, drop_duplicate: Optional[Any] = None,
    drop_correlated_threshold: float = 0.8,
    drop_correlated_method: str = "variance", correlation_method: str = "spearman",
    aggregation_method: str = "intersection", min_samples_per_segment: int = 100,
) -> Tuple[List[str], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if segments is None:
        segments = []
    if not isinstance(segments, list):
        raise TypeError(f"segments deve ser uma lista ou None, recebeu: {type(segments)}")
    for seg in segments:
        if seg not in df_train.columns:
            raise ValueError(f"Coluna de segmentação '{seg}' não encontrada no DataFrame")
    if aggregation_method not in ["intersection", "union"]:
        raise ValueError(f"aggregation_method deve ser intersection ou union, recebeu: {aggregation_method}")

    excluidas_rows, metricas_rows, variaveis_por_segmento_rows = [], [], []
    if not segments:
        features_finais, excluded_vars, metrics = limpeza_variaveis_otimizada_final(
            df_train, target, features, drop_missing, drop_constant, drop_duplicate,
            drop_correlated_threshold, drop_correlated_method, correlation_method,
        )
        segment_info = {"tabela": nome_tabela, "segment_level": "N/A", "segment_value": "GERAL"}
        _registrar_resultados(
            features_finais, excluded_vars, metrics, df_train, segment_info, "geral",
            excluidas_rows, metricas_rows, variaveis_por_segmento_rows,
        )
    else:
        features_finais = _processar_nivel_segmentacao(
            df_train, target, features, nome_tabela, drop_missing, segments, 0, {},
            drop_constant, drop_duplicate, drop_correlated_threshold,
            drop_correlated_method, correlation_method, min_samples_per_segment,
            aggregation_method, excluidas_rows, metricas_rows, variaveis_por_segmento_rows,
        )
    return (
        features_finais, pd.DataFrame(excluidas_rows), pd.DataFrame(metricas_rows),
        pd.DataFrame(variaveis_por_segmento_rows),
    )


def _write_frame(path: Path, frame: pd.DataFrame, identity: dict, columns: List[str]) -> None:
    result = frame.copy()
    for key, value in identity.items():
        result[key] = value
    for column in columns:
        if column not in result.columns:
            result[column] = pd.Series(dtype="object")
    result.to_csv(path, index=False, encoding="utf-8")


def salvar_resultados(output_dir: Path, spec: dict, selected: List[str],
                      excluded: pd.DataFrame, metrics: pd.DataFrame,
                      per_segment: pd.DataFrame, n_samples: int, elapsed: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    identity = {"run_id": spec["run_id"], "book": spec["book"],
                "batch_index": spec["batch_index"], "feature_hash": spec["feature_hash"]}
    _write_frame(output_dir / "variaveis_excluidas.csv", excluded, identity,
                 ["tabela", "etapa", "variavel"])
    _write_frame(output_dir / "metricas.csv", metrics, identity,
                 ["tabela", "etapa", "n_features_inicial", "n_features_final", "n_samples"])
    _write_frame(output_dir / "variaveis_por_segmento.csv", per_segment, identity,
                 ["tabela", "nivel", "variavel"])
    final = pd.DataFrame({"variavel": list(dict.fromkeys(selected)),
                          "tipo": "selecionada"})
    _write_frame(output_dir / "variaveis_finais.csv", final, identity,
                 ["variavel", "tipo"])
    summary = {**identity, "status": "ok" if selected else "empty",
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "features_iniciais": len(spec["feature_columns"]),
               "features_finais": len(selected), "n_samples": n_samples,
               "elapsed_seconds": round(elapsed, 1)}
    (output_dir / "resumo.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def run_task(spec: dict, output_dir: Path) -> dict:
    t0 = datetime.now(timezone.utc)
    frame = carrega_tabela(spec)
    if len(frame) != spec["profile_rows"]:
        raise ValueError(f"Joined row count changed: {len(frame)} vs planned {spec['profile_rows']}")
    feature_names = [column["name"] for column in spec["feature_columns"]]
    for name in feature_names:
        frame[name] = pd.to_numeric(frame[name], errors="raise").astype("float64")
    if feature_names:
        selected, excluded, metrics, per_segment = limpeza_variaveis_hierarquica_final(
            df_train=frame, target=spec["target"], features=feature_names,
            nome_tabela=spec["book"], drop_missing=spec.get("drop_missing", 0.05),
            segments=spec.get("segments", _DEFAULT_SEGMENTS),
            drop_correlated_threshold=spec.get("corr_threshold", 0.8),
            correlation_method="spearman", aggregation_method=spec.get("agg_method", "union"),
            min_samples_per_segment=spec.get("min_samples", 100),
        )
    else:
        selected, excluded, metrics, per_segment = [], pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    salvar_resultados(output_dir, spec, selected, excluded, metrics, per_segment, len(frame), elapsed)
    return {"selected": selected, "n_samples": len(frame)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature selection for one planned book batch")
    parser.add_argument("--task-spec", required=True, help="S3 URI or local JSON path")
    parser.add_argument("--output-dir", default="/opt/ml/processing/output")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    t0 = datetime.now(timezone.utc)
    spec = None
    try:
        spec = _load_spec(args.task_spec)
        run_task(spec, output_dir)
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        identity = {key: spec.get(key) for key in ("run_id", "book", "batch_index", "feature_hash")} if spec else {}
        summary = {**identity, "status": "error", "error": str(exc),
                   "elapsed_seconds": round((datetime.now(timezone.utc)-t0).total_seconds(), 1)}
        (output_dir / "resumo.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (output_dir / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
