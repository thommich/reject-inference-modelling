"""Plan and run first-stage feature selection in SageMaker Studio.

The Processing image remains Scikit-learn 1.2-1 for the deployment environment.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

FRAMEWORK_VERSION = "1.2-1"
CATALOG_DATE = "2026-10-29T16:50:09Z"
CATALOG_URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonSageMaker/current/sa-east-1/index.json"
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_SEGMENTS = ["produto_final_consolidado", "bancos", "spi", "faixa_idade"]
DEFAULT_METADATA = {"pk_riznumdoc_xx", "cod_idef_pess", "target_final_amostra", "amostra",
                    "safra", "produto_final_consolidado", "bancos", "spi", "faixa_idade",
                    "correntista", "contrato_6m", "publico_final", "pk_riznumdoc_str_xx",
                    "pk_datref_xx", "pk_tpp_xx", "pk_datver_xx", "anomes", "anomesdia",
                    "data_ref_di", "kjoin", "ano_dat_rfrc", "mes_dat_rfrc", "dia_dat_rfrc",
                    "num_cpf_cnpj_clie", "num_mode_stto_crto", "d_num_cpf", "cnpj_fonte_pagadora",
                    "pk_idef_pess_xx", "tipo_pessoa", "anomesdia_processamento", "ano_mes_dia",
                    "dat_rfrc_mode", "dat_vers_mode"}
NUMERIC_TYPES = ("tinyint", "smallint", "integer", "int", "bigint", "float", "real", "double", "decimal(")

INSTANCE_TIERS = ['ml.m5.12xlarge',
 'ml.m6i.8xlarge',
 'ml.m6i.12xlarge',
 'ml.m7i.8xlarge',
 'ml.m7i.12xlarge',
 'ml.m5.16xlarge',
 'ml.m6i.16xlarge',
 'ml.m7i.16xlarge',
 'ml.m5.24xlarge',
 'ml.m6i.24xlarge',
 'ml.m7i.24xlarge',
 'ml.m7i.48xlarge',
 'ml.m8i.8xlarge',
 'ml.m8i.12xlarge',
 'ml.m8i.16xlarge',
 'ml.m8i.24xlarge',
 'ml.m8i.48xlarge',
 'ml.m8i.96xlarge',
 'ml.r5.4xlarge',
 'ml.r6i.8xlarge',
 'ml.r7i.8xlarge',
 'ml.r5.8xlarge',
 'ml.r5.12xlarge',
 'ml.r6i.12xlarge',
 'ml.r7i.12xlarge',
 'ml.r5.16xlarge',
 'ml.r6i.16xlarge',
 'ml.r7i.16xlarge',
 'ml.r5.24xlarge',
 'ml.r6i.24xlarge',
 'ml.r7i.24xlarge',
 'ml.r7i.48xlarge',
 'ml.r8i.8xlarge',
 'ml.r8i.12xlarge',
 'ml.r8i.16xlarge',
 'ml.r8i.24xlarge',
 'ml.r8i.48xlarge',
 'ml.r8i.96xlarge',
 'ml.c5.18xlarge',
 'ml.c6i.12xlarge',
 'ml.c7i.12xlarge',
 'ml.c6i.16xlarge',
 'ml.c7i.16xlarge',
 'ml.c7i.24xlarge',
 'ml.c8i.16xlarge',
 'ml.c8i.24xlarge',
 'ml.c7i.48xlarge',
 'ml.c8i.48xlarge',
 'ml.c8i.96xlarge',
 'ml.m7i-flex.8xlarge',
 'ml.m7i-flex.12xlarge',
 'ml.m7i-flex.16xlarge',
 'ml.c7i-flex.12xlarge',
 'ml.c7i-flex.16xlarge',
 'ml.g4dn.8xlarge',
 'ml.g5.8xlarge',
 'ml.g6.8xlarge',
 'ml.g4dn.12xlarge',
 'ml.g5.12xlarge',
 'ml.g6.12xlarge',
 'ml.g5.16xlarge',
 'ml.g6.16xlarge',
 'ml.g5.24xlarge',
 'ml.g6.24xlarge',
 'ml.g5.48xlarge',
 'ml.g6.48xlarge',
 'ml.p3.8xlarge',
 'ml.p3.16xlarge',
 'ml.p5.4xlarge',
 'ml.m4.10xlarge',
 'ml.m4.16xlarge']

INSTANCE_CATALOG = {'ml.m5.12xlarge': {'memory_gib': 192, 'usd_per_hour': 4.406, 'source': 'sagemaker_catalog'},
 'ml.m6i.8xlarge': {'memory_gib': 128, 'usd_per_hour': 2.938, 'source': 'sagemaker_catalog'},
 'ml.m6i.12xlarge': {'memory_gib': 192, 'usd_per_hour': 4.406, 'source': 'sagemaker_catalog'},
 'ml.m7i.8xlarge': {'memory_gib': 128, 'usd_per_hour': 3.08448, 'source': 'sagemaker_catalog'},
 'ml.m7i.12xlarge': {'memory_gib': 192, 'usd_per_hour': 4.62672, 'source': 'sagemaker_catalog'},
 'ml.m5.16xlarge': {'memory_gib': 256, 'usd_per_hour': None, 'source': 'ec2_unpriced'},
 'ml.m6i.16xlarge': {'memory_gib': 256, 'usd_per_hour': 5.875, 'source': 'sagemaker_catalog'},
 'ml.m7i.16xlarge': {'memory_gib': 256, 'usd_per_hour': 6.16896, 'source': 'sagemaker_catalog'},
 'ml.m5.24xlarge': {'memory_gib': 384, 'usd_per_hour': 8.813, 'source': 'sagemaker_catalog'},
 'ml.m6i.24xlarge': {'memory_gib': 384, 'usd_per_hour': 8.813, 'source': 'sagemaker_catalog'},
 'ml.m7i.24xlarge': {'memory_gib': 384, 'usd_per_hour': 9.25344, 'source': 'sagemaker_catalog'},
 'ml.m7i.48xlarge': {'memory_gib': 768, 'usd_per_hour': 18.50688, 'source': 'sagemaker_catalog'},
 'ml.m8i.8xlarge': {'memory_gib': 128, 'usd_per_hour': 3.238656, 'source': 'sagemaker_catalog'},
 'ml.m8i.12xlarge': {'memory_gib': 192, 'usd_per_hour': 4.857984, 'source': 'sagemaker_catalog'},
 'ml.m8i.16xlarge': {'memory_gib': 256, 'usd_per_hour': 6.477312, 'source': 'sagemaker_catalog'},
 'ml.m8i.24xlarge': {'memory_gib': 384, 'usd_per_hour': 9.715968, 'source': 'sagemaker_catalog'},
 'ml.m8i.48xlarge': {'memory_gib': 768, 'usd_per_hour': 19.4319, 'source': 'sagemaker_catalog'},
 'ml.m8i.96xlarge': {'memory_gib': 1536, 'usd_per_hour': 38.8639, 'source': 'sagemaker_catalog'},
 'ml.r5.4xlarge': {'memory_gib': 128, 'usd_per_hour': 1.93, 'source': 'sagemaker_catalog'},
 'ml.r6i.8xlarge': {'memory_gib': 256, 'usd_per_hour': 3.8592, 'source': 'sagemaker_catalog'},
 'ml.r7i.8xlarge': {'memory_gib': 256, 'usd_per_hour': 4.05216, 'source': 'sagemaker_catalog'},
 'ml.r5.8xlarge': {'memory_gib': 256, 'usd_per_hour': 3.859, 'source': 'sagemaker_catalog'},
 'ml.r5.12xlarge': {'memory_gib': 384, 'usd_per_hour': 5.789, 'source': 'sagemaker_catalog'},
 'ml.r6i.12xlarge': {'memory_gib': 384, 'usd_per_hour': 5.7888, 'source': 'sagemaker_catalog'},
 'ml.r7i.12xlarge': {'memory_gib': 384, 'usd_per_hour': 6.07824, 'source': 'sagemaker_catalog'},
 'ml.r5.16xlarge': {'memory_gib': 512, 'usd_per_hour': 7.718, 'source': 'sagemaker_catalog'},
 'ml.r6i.16xlarge': {'memory_gib': 512, 'usd_per_hour': 7.7184, 'source': 'sagemaker_catalog'},
 'ml.r7i.16xlarge': {'memory_gib': 512, 'usd_per_hour': 8.10432, 'source': 'sagemaker_catalog'},
 'ml.r5.24xlarge': {'memory_gib': 768, 'usd_per_hour': 11.578, 'source': 'sagemaker_catalog'},
 'ml.r6i.24xlarge': {'memory_gib': 768, 'usd_per_hour': 11.5776, 'source': 'sagemaker_catalog'},
 'ml.r7i.24xlarge': {'memory_gib': 768, 'usd_per_hour': 12.15648, 'source': 'sagemaker_catalog'},
 'ml.r7i.48xlarge': {'memory_gib': 1536, 'usd_per_hour': 24.31296, 'source': 'sagemaker_catalog'},
 'ml.r8i.8xlarge': {'memory_gib': 256, 'usd_per_hour': 4.25472, 'source': 'sagemaker_catalog'},
 'ml.r8i.12xlarge': {'memory_gib': 384, 'usd_per_hour': 6.38208, 'source': 'sagemaker_catalog'},
 'ml.r8i.16xlarge': {'memory_gib': 512, 'usd_per_hour': 8.50944, 'source': 'sagemaker_catalog'},
 'ml.r8i.24xlarge': {'memory_gib': 768, 'usd_per_hour': 12.76416, 'source': 'sagemaker_catalog'},
 'ml.r8i.48xlarge': {'memory_gib': 1536, 'usd_per_hour': 25.5283, 'source': 'sagemaker_catalog'},
 'ml.r8i.96xlarge': {'memory_gib': 3072, 'usd_per_hour': 51.0566, 'source': 'sagemaker_catalog'},
 'ml.c5.18xlarge': {'memory_gib': 144, 'usd_per_hour': 5.659, 'source': 'sagemaker_catalog'},
 'ml.c6i.12xlarge': {'memory_gib': 96, 'usd_per_hour': 3.773, 'source': 'sagemaker_catalog'},
 'ml.c7i.12xlarge': {'memory_gib': 96, 'usd_per_hour': 3.96144, 'source': 'sagemaker_catalog'},
 'ml.c6i.16xlarge': {'memory_gib': 128, 'usd_per_hour': 5.03, 'source': 'sagemaker_catalog'},
 'ml.c7i.16xlarge': {'memory_gib': 128, 'usd_per_hour': 5.28192, 'source': 'sagemaker_catalog'},
 'ml.c7i.24xlarge': {'memory_gib': 192, 'usd_per_hour': 7.92288, 'source': 'sagemaker_catalog'},
 'ml.c8i.16xlarge': {'memory_gib': 128, 'usd_per_hour': 5.546112, 'source': 'sagemaker_catalog'},
 'ml.c8i.24xlarge': {'memory_gib': 192, 'usd_per_hour': 8.319168, 'source': 'sagemaker_catalog'},
 'ml.c7i.48xlarge': {'memory_gib': 384, 'usd_per_hour': 15.84576, 'source': 'sagemaker_catalog'},
 'ml.c8i.48xlarge': {'memory_gib': 384, 'usd_per_hour': 16.6383, 'source': 'sagemaker_catalog'},
 'ml.c8i.96xlarge': {'memory_gib': 768, 'usd_per_hour': 33.2767, 'source': 'sagemaker_catalog'},
 'ml.m7i-flex.8xlarge': {'memory_gib': 128, 'usd_per_hour': 2.9303, 'source': 'sagemaker_catalog'},
 'ml.m7i-flex.12xlarge': {'memory_gib': 192, 'usd_per_hour': 4.3955, 'source': 'sagemaker_catalog'},
 'ml.m7i-flex.16xlarge': {'memory_gib': 256, 'usd_per_hour': 5.8606, 'source': 'sagemaker_catalog'},
 'ml.c7i-flex.12xlarge': {'memory_gib': 96, 'usd_per_hour': 3.7634, 'source': 'ec2_override'},
 'ml.c7i-flex.16xlarge': {'memory_gib': 128, 'usd_per_hour': 5.0178, 'source': 'sagemaker_catalog'},
 'ml.g4dn.8xlarge': {'memory_gib': 128, 'usd_per_hour': 4.622, 'source': 'sagemaker_catalog'},
 'ml.g5.8xlarge': {'memory_gib': 128, 'usd_per_hour': 5.20139, 'source': 'sagemaker_catalog'},
 'ml.g6.8xlarge': {'memory_gib': 128, 'usd_per_hour': 4.2801, 'source': 'sagemaker_catalog'},
 'ml.g4dn.12xlarge': {'memory_gib': 192, 'usd_per_hour': 8.311, 'source': 'sagemaker_catalog'},
 'ml.g5.12xlarge': {'memory_gib': 192, 'usd_per_hour': 12.05159, 'source': 'sagemaker_catalog'},
 'ml.g6.12xlarge': {'memory_gib': 192, 'usd_per_hour': 9.7772625, 'source': 'sagemaker_catalog'},
 'ml.g5.16xlarge': {'memory_gib': 256, 'usd_per_hour': 8.70299, 'source': 'sagemaker_catalog'},
 'ml.g6.16xlarge': {'memory_gib': 256, 'usd_per_hour': 7.21735, 'source': 'sagemaker_catalog'},
 'ml.g5.24xlarge': {'memory_gib': 384, 'usd_per_hour': 17.30398, 'source': 'sagemaker_catalog'},
 'ml.g6.24xlarge': {'memory_gib': 384, 'usd_per_hour': 14.1831375, 'source': 'sagemaker_catalog'},
 'ml.g5.48xlarge': {'memory_gib': 768, 'usd_per_hour': 34.60795, 'source': 'sagemaker_catalog'},
 'ml.g6.48xlarge': {'memory_gib': 768, 'usd_per_hour': 28.3662875, 'source': 'sagemaker_catalog'},
 'ml.p3.8xlarge': {'memory_gib': 244, 'usd_per_hour': None, 'source': 'ec2_unpriced'},
 'ml.p3.16xlarge': {'memory_gib': 488, 'usd_per_hour': None, 'source': 'ec2_unpriced'},
 'ml.p5.4xlarge': {'memory_gib': 256, 'usd_per_hour': 13.29216, 'source': 'sagemaker_catalog'},
 'ml.m4.10xlarge': {'memory_gib': 160, 'usd_per_hour': 3.816, 'source': 'sagemaker_catalog'},
 'ml.m4.16xlarge': {'memory_gib': 256, 'usd_per_hour': 6.106, 'source': 'sagemaker_catalog'}}

BOOKS_MLTOOLS = ['BC', 'BF', 'CH', 'CN', 'DA', 'DE', 'IM', 'RC', 'TR', 'TT', 'V2']
BOOKS_CUSTOM = ['H3',
 'PIX',
 'SP_CR',
 'SP_BL',
 'SP_CC',
 'AF',
 'AP',
 'TG',
 'HG',
 'AG',
 'IN',
 'RV',
 'BJ',
 'OPF_TR',
 'OPF_CT',
 'OPF_SL',
 'SD']
TABELAS_THOTH = {'AU_A': 'lasgvki_emprestimos_mdl_thoth_au_autorizacoes_a',
 'AU_B': 'lasgvki_emprestimos_mdl_thoth_au_autorizacoes_b',
 'AU_C': 'lasgvki_emprestimos_mdl_thoth_au_autorizacoes_c',
 'BX_LIQ_A': 'lasgvki_emprestimos_mdl_thoth_bx_liq_apontamentosliquidados_a',
 'BX_LIQ_B': 'lasgvki_emprestimos_mdl_thoth_bx_liq_apontamentosliquidados_b',
 'BX_LIQ_C': 'lasgvki_emprestimos_mdl_thoth_bx_liq_apontamentosliquidados_c',
 'BX_VIG_A': 'lasgvki_emprestimos_mdl_thoth_bx_vig_apontamentosvigente_a',
 'BX_VIG_B': 'lasgvki_emprestimos_mdl_thoth_bx_vig_apontamentosvigente_b',
 'CC_A': 'lasgvki_emprestimos_mdl_thoth_fluxo_fluxodeconta_a',
 'CC_B': 'lasgvki_emprestimos_mdl_thoth_fluxo_fluxodeconta_b',
 'CC_C': 'lasgvki_emprestimos_mdl_thoth_fluxo_fluxodeconta_c',
 'FT': 'lasgvki_emprestimos_mdl_thoth_ft_faturasnpc',
 'PF_A': 'lasgvki_emprestimos_mdl_thoth_pf_produtosfinanceiros_a',
 'PF_B': 'lasgvki_emprestimos_mdl_thoth_pf_produtosfinanceiros_b'}

def _ident(name: str) -> str:
    if not IDENTIFIER.fullmatch(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


def _table(name: str) -> str:
    parts = name.split(".")
    if len(parts) != 2:
        raise ValueError(f"Expected database.table: {name!r}")
    return ".".join(_ident(part) for part in parts)


def _s3_parts(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://") or "/" not in uri[5:]:
        raise ValueError(f"Invalid S3 URI: {uri!r}")
    return tuple(uri[5:].split("/", 1))


def _put_json(s3: Any, uri: str, value: dict) -> None:
    bucket, key = _s3_parts(uri)
    s3.put_object(Bucket=bucket, Key=key,
                  Body=json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"),
                  ContentType="application/json")


def _get_json(s3: Any, uri: str) -> dict:
    bucket, key = _s3_parts(uri)
    return json.loads(s3.get_object(Bucket=bucket, Key=key)["Body"].read())


def _one(athena: Any, sql: str) -> int:
    frame = athena.query(sql)
    if frame.empty:
        return 0
    return int(frame.iloc[0, 0])


def _sql_value(value: Any) -> str:
    if pd.isna(value):
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _allocate_strata(strata: pd.DataFrame, target: int) -> list[int]:
    counts = [int(v) for v in strata["total_estrato"]]
    total = sum(counts)
    if target <= 0 or total <= 0 or target > total:
        raise ValueError(f"Sample target {target} must be between 1 and population {total}")
    exact = [target * count / total for count in counts]
    allocated = [math.floor(value) for value in exact]
    remainder = target - sum(allocated)
    order = sorted(range(len(counts)), key=lambda i: (-(exact[i] - allocated[i]), -counts[i], i))
    for i in order:
        if remainder == 0:
            break
        if allocated[i] < counts[i]:
            allocated[i] += 1
            remainder -= 1
    if remainder or sum(allocated) != target:
        raise RuntimeError("Unable to allocate the requested sample")
    return allocated


def _assert_unique(athena: Any, table: str, columns: list[str], label: str) -> None:
    names = ", ".join(_ident(name) for name in columns)
    nulls = " OR ".join(f"{_ident(name)} IS NULL" for name in columns)
    if _one(athena, f"SELECT COUNT(*) FROM {_table(table)} WHERE {nulls}"):
        raise ValueError(f"{label} contains null key values: {columns}")
    dup = athena.query(f"SELECT {names}, COUNT(*) AS n FROM {_table(table)} "
                       f"GROUP BY {names} HAVING COUNT(*) > 1 LIMIT 1")
    if not dup.empty:
        raise ValueError(f"{label} is not unique on {columns}")


def prepare_sample(athena: Any, base_table: str, run_id: str,
                   target: int = 2045740) -> tuple[str, int]:
    """Create one run-scoped, null-safe customer-vintage sample."""
    _assert_unique(athena, base_table, ["pk_riznumdoc_xx", "safra"], "base table")
    db = base_table.split(".", 1)[0]
    suffix = run_id.replace("-", "_")
    allocation = f"{db}.tmp_amostra_fs_aloc_{suffix}"
    sample = f"{db}.tmp_amostra_fs_ids_{suffix}"
    segments = ", ".join(_ident(name) for name in DEFAULT_SEGMENTS)
    strata = athena.query(f"SELECT {segments}, COUNT(*) AS total_estrato "
                          f"FROM {_table(base_table)} GROUP BY {segments}")
    counts = _allocate_strata(strata, target)
    cast_fields = ", ".join(f"CAST({_ident(name)} AS varchar) AS {_ident(name)}"
                             for name in DEFAULT_SEGMENTS)
    athena.execute(f"CREATE TABLE {_table(allocation)} AS SELECT {cast_fields}, "
                   f"CAST(NULL AS bigint) AS n_alvo FROM {_table(base_table)} WHERE FALSE")
    values = []
    for (_, row), count in zip(strata.iterrows(), counts):
        values.append("(" + ", ".join([*(_sql_value(row[name]) for name in DEFAULT_SEGMENTS),
                                         str(count)]) + ")")
    for start in range(0, len(values), 100):
        athena.execute(f"INSERT INTO {_table(allocation)} VALUES " + ", ".join(values[start:start+100]))
    cast_rank = ", ".join(f"CAST({_ident(name)} AS varchar) AS {_ident(name)}"
                          for name in DEFAULT_SEGMENTS)
    partition = ", ".join(_ident(name) for name in DEFAULT_SEGMENTS)
    matches = " AND ".join(f"r.{_ident(name)} IS NOT DISTINCT FROM a.{_ident(name)}"
                           for name in DEFAULT_SEGMENTS)
    pk, vintage = _ident("pk_riznumdoc_xx"), _ident("safra")
    athena.execute(
        f"CREATE TABLE {_table(sample)} AS SELECT r.{pk}, r.{vintage} FROM ("
        f"SELECT {pk}, {vintage}, {cast_rank}, ROW_NUMBER() OVER ("
        f"PARTITION BY {partition} ORDER BY RANDOM()) AS rn FROM {_table(base_table)}"
        f") r JOIN {_table(allocation)} a ON {matches} WHERE r.rn <= a.n_alvo"
    )
    actual = _one(athena, f"SELECT COUNT(*) FROM {_table(sample)}")
    if actual != target:
        raise ValueError(f"Sample contains {actual} rows, expected {target}")
    _assert_unique(athena, sample, ["pk_riznumdoc_xx", "safra"], "sample")
    return sample, actual


def _glue_columns(glue: Any, table: str) -> dict[str, str] | None:
    database, name = table.split(".", 1)
    try:
        result = glue.get_table(DatabaseName=database, Name=name)["Table"]
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code")
        if code in ("EntityNotFoundException", "ResourceNotFoundException"):
            return None
        raise
    columns = result.get("StorageDescriptor", {}).get("Columns", []) + result.get("PartitionKeys", [])
    return {column["Name"]: column["Type"].lower() for column in columns}


def _book_registry(database: str) -> dict[str, dict]:
    registry = {}
    for book in BOOKS_MLTOOLS:
        registry[book] = {"group": "MLTools", "table": f"{database}.lasgvki_emprestimos_amostra_npm_explicativas_{book.lower()}_left",
                          "join_key": "pk_riznumdoc_xx"}
    for book in BOOKS_CUSTOM:
        registry[book] = {"group": "Customizados", "table": f"{database}.lasgvki_emprestimos_{book.lower()}_explicativas",
                          "join_key": "pk_riznumdoc_xx"}
    for book, table in TABELAS_THOTH.items():
        registry[book] = {"group": "Thoth", "table": f"{database}.{table}",
                          "join_key": "cod_idef_pess"}
    return registry


def _is_numeric(type_name: str) -> bool:
    return type_name.startswith(NUMERIC_TYPES)


def _feature_candidates(base_columns: dict, book_columns: dict,
                        join_key: str, target: str, segments: list[str]) -> tuple[list[dict], list[str]]:
    required = set(["pk_riznumdoc_xx", "safra", join_key, target, *segments])
    if not required.issubset(base_columns):
        raise ValueError(f"Base is missing columns: {sorted(required - base_columns.keys())}")
    if join_key not in book_columns:
        raise ValueError(f"Book is missing join key {join_key}")
    excluded = DEFAULT_METADATA | required
    candidates, nonnumeric = [], []
    for source, columns in (("b", base_columns), ("f", book_columns)):
        for name, type_name in columns.items():
            if name in excluded:
                continue
            _ident(name)
            if _is_numeric(type_name):
                candidates.append({"source": source, "name": name})
            else:
                nonnumeric.append(f"{source}.{name} ({type_name})")
    names = [column["name"] for column in candidates]
    if len(names) != len(set(names)):
        raise ValueError("Base and book have colliding numeric feature names")
    return candidates, nonnumeric


def _join_sql(base: str, sample: str, feature: str, join_key: str) -> str:
    pk, vintage, key = _ident("pk_riznumdoc_xx"), _ident("safra"), _ident(join_key)
    return (f"FROM {_table(sample)} a JOIN {_table(base)} b ON b.{pk}=a.{pk} "
            f"AND b.{vintage}=a.{vintage} LEFT JOIN {_table(feature)} f ON b.{key}=f.{key}")


def _check_book_join(athena: Any, base: str, sample: str,
                     feature: str, join_key: str, expected_rows: int) -> None:
    key, pk, vintage = _ident(join_key), _ident("pk_riznumdoc_xx"), _ident("safra")
    duplicate = athena.query(
        f"SELECT f.{key}, COUNT(*) AS n FROM {_table(feature)} f JOIN ("
        f"SELECT DISTINCT b.{key} FROM {_table(sample)} a JOIN {_table(base)} b "
        f"ON b.{pk}=a.{pk} AND b.{vintage}=a.{vintage}"
        f") k ON f.{key}=k.{key} GROUP BY f.{key} HAVING COUNT(*)>1 LIMIT 1"
    )
    if not duplicate.empty:
        raise ValueError(f"Feature-side key {join_key} is not unique for sampled records")
    joined = _one(athena, "SELECT COUNT(*) " + _join_sql(base, sample, feature, join_key))
    if joined != expected_rows:
        raise ValueError(f"Join has {joined} rows, expected {expected_rows}")


def _profile_shared_bytes(athena: Any, base: str, sample: str, feature: str,
                          join_key: str, target: str, segments: list[str]) -> int:
    shared = list(dict.fromkeys(["pk_riznumdoc_xx", "safra", target, *segments]))
    select = ", ".join(f"b.{_ident(name)} AS {_ident(name)}" for name in shared)
    preview = athena.query(f"SELECT {select} " + _join_sql(base, sample, feature, join_key) + " LIMIT 256")
    if preview.empty:
        raise ValueError("Joined sample is empty")
    return max(64, math.ceil(preview.memory_usage(deep=True).sum() / len(preview)))


def estimate_peak_gib(n_rows: int, n_features: int, shared_row_bytes: int) -> float:
    """Conservative model; calibrate its array multiplier using real peak RSS."""
    bytes_total = (2 * 1024**3 + n_rows * shared_row_bytes
                   + 7 * 8 * n_rows * n_features + 8 * n_features**2
                   + 96 * n_features * (n_features - 1) // 2)
    return bytes_total / 1024**3


def eligible_instances(peak_gib: float, min_memory_gib: int = 0,
                       excluded: set[str] | None = None) -> list[str]:
    excluded = excluded or set()
    return sorted((name for name in INSTANCE_TIERS
                   if INSTANCE_CATALOG[name]["usd_per_hour"] is not None
                   and INSTANCE_CATALOG[name]["memory_gib"] >= min_memory_gib
                   and peak_gib <= 0.60 * INSTANCE_CATALOG[name]["memory_gib"]
                   and name not in excluded),
                  key=lambda name: (INSTANCE_CATALOG[name]["usd_per_hour"],
                                    INSTANCE_CATALOG[name]["memory_gib"], name))


def _spec_hash(columns: list[dict]) -> str:
    return hashlib.sha256(json.dumps(columns, sort_keys=True).encode()).hexdigest()


def _task_spec(run_id: str, book: str, book_info: dict, config: dict,
              sample: str, columns: list[dict], index: str,
              n_rows: int, shared_bytes: int, instance: str,
              depth: int = 0) -> dict:
    peak = estimate_peak_gib(n_rows, len(columns), shared_bytes)
    return {"run_id": run_id, "book": book, "group": book_info["group"],
            "batch_index": index, "batch_count": None, "feature_columns": columns,
            "feature_hash": _spec_hash(columns), "base_table": config["base_table"],
            "feature_table": book_info["table"], "sample_table": sample,
            "join_key": book_info["join_key"], "target": config["target"],
            "segments": config["segments"], "database": config["database"],
            "workgroup": config["workgroup"], "athena_output": config["athena_output"],
            "region": config.get("region", "sa-east-1"),
            "drop_missing": config["drop_missing"], "corr_threshold": config["corr_threshold"],
            "agg_method": config["agg_method"], "min_samples": config["min_samples"],
            "instance_type": instance, "estimated_peak_gib": round(peak, 3),
            "profile_rows": n_rows, "shared_row_bytes": shared_bytes, "split_depth": depth}


def plan_book(run_id: str, book: str, book_info: dict, config: dict,
              sample: str, n_rows: int, shared_bytes: int,
              candidates: list[dict]) -> list[dict]:
    if not candidates:
        raise ValueError("No numeric candidate features")
    max_columns = config.get("max_corr_columns", 1024)
    if max_columns < 1:
        raise ValueError("max_corr_columns must be positive")
    tasks, offset = [], 0
    while offset < len(candidates):
        width = min(max_columns, len(candidates) - offset)
        while width and not eligible_instances(estimate_peak_gib(n_rows, width, shared_bytes)):
            width //= 2
        if width == 0:
            raise ValueError("Even a one-column task exceeds all schedulable memory budgets")
        columns = candidates[offset:offset+width]
        instance = eligible_instances(estimate_peak_gib(n_rows, width, shared_bytes))[0]
        spec = _task_spec(run_id, book, book_info, config, sample, columns,
                          str(len(tasks)), n_rows, shared_bytes, instance)
        tasks.append(spec)
        offset += width
    for spec in tasks:
        spec["batch_count"] = len(tasks)
    return tasks


def default_config(bucket: str, *, base_table: str = "workspace_db.tmp_cubo_vol_base_features_direta",
                   database: str = "workspace_db", workgroup: str = "analytics-workgroup",
                   athena_output: str | None = None) -> dict:
    return {"base_table": base_table, "database": database,
            "target": "target_final_amostra", "segments": DEFAULT_SEGMENTS.copy(),
            "sample_target": 2045740, "drop_missing": 0.05,
            "corr_threshold": 0.8, "agg_method": "union", "min_samples": 100,
            "max_concurrent": 10, "max_corr_columns": 1024, "poll_interval": 30,
            "workgroup": workgroup,
            "athena_output": athena_output or f"s3://{bucket}/athena-results/",
            "region": "sa-east-1"}


def _manifest_uri(bucket: str, run_id: str) -> str:
    return f"s3://{bucket}/fs-results/{run_id}/manifest.json"


def _task_uri(bucket: str, run_id: str, task_id: str) -> str:
    return f"s3://{bucket}/fs-results/{run_id}/specs/{task_id}.json"


def _output_uri(bucket: str, run_id: str, book: str, task_id: str) -> str:
    return f"s3://{bucket}/fs-results/{run_id}/{book}/{task_id}/"


def _save_manifest(s3: Any, bucket: str, manifest: dict) -> None:
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _put_json(s3, _manifest_uri(bucket, manifest["run_id"]), manifest)


def _add_task(s3: Any, bucket: str, manifest: dict, task_id: str, spec: dict) -> None:
    uri = _task_uri(bucket, manifest["run_id"], task_id)
    _put_json(s3, uri, spec)
    manifest["tasks"][task_id] = {
        "status": "pending", "spec_uri": uri, "spec": spec,
        "output_uri": _output_uri(bucket, manifest["run_id"], spec["book"], task_id),
        "job_name": None, "attempts": 0, "tried_instances": [], "failure_reason": None,
        "poll_errors": 0, "capacity_rounds": 0, "history": []}


def plan_run(athena: Any, glue: Any, s3: Any, bucket: str,
             config: dict, run_id: str | None = None) -> dict:
    run_id = run_id or (datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%S")
                        + "_" + uuid.uuid4().hex[:8])
    if not re.fullmatch(r"[a-z0-9_]{8,40}", run_id):
        raise ValueError("run_id must contain 8-40 lowercase letters, digits, or underscores")
    if not isinstance(config.get("max_concurrent"), int) or not 1 <= config["max_concurrent"] <= 10:
        raise ValueError("max_concurrent must be between 1 and 10")
    if config["database"] != config["base_table"].split(".", 1)[0]:
        raise ValueError("database and base_table database differ")
    base_columns = _glue_columns(glue, config["base_table"])
    if base_columns is None:
        raise ValueError(f"Base table is missing: {config['base_table']}")
    for required in ["pk_riznumdoc_xx", "safra", config["target"], *config["segments"]]:
        if required not in base_columns:
            raise ValueError(f"Base table is missing {required}")
    sample, sample_count = prepare_sample(athena, config["base_table"], run_id,
                                         config["sample_target"])
    manifest = {"version": 1, "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "catalog_date": CATALOG_DATE, "catalog_url": CATALOG_URL,
                "sample_table": sample, "sample_count": sample_count,
                "config": config, "books": {}, "tasks": {}, "code_uri": None}
    registry = _book_registry(config["database"])
    for book, info in registry.items():
        record = {**info, "status": "planning", "reason": None, "n_features": 0,
                  "nonnumeric": [], "task_ids": []}
        manifest["books"][book] = record
        try:
            columns = _glue_columns(glue, info["table"])
            if columns is None:
                record["status"] = "skipped"
                record["reason"] = "Glue table not found"
                continue
            candidates, nonnumeric = _feature_candidates(
                base_columns, columns, info["join_key"], config["target"], config["segments"])
            record["n_features"] = len(candidates)
            record["nonnumeric"] = nonnumeric
            _check_book_join(athena, config["base_table"], sample, info["table"],
                             info["join_key"], sample_count)
            if not candidates:
                record["status"] = "skipped"
                record["reason"] = "No numeric candidate features"
                continue
            shared_bytes = _profile_shared_bytes(
                athena, config["base_table"], sample, info["table"],
                info["join_key"], config["target"], config["segments"])
            specs = plan_book(run_id, book, info, config, sample,
                              sample_count, shared_bytes, candidates)
            for index, spec in enumerate(specs):
                task_id = f"{book.lower()}_b{index}"
                _add_task(s3, bucket, manifest, task_id, spec)
                record["task_ids"].append(task_id)
            record["status"] = "pending"
        except Exception as exc:
            record["status"] = "preflight_failed"
            record["reason"] = str(exc)
    _save_manifest(s3, bucket, manifest)
    return manifest


def _job_name(run_id: str, task_id: str, attempt: int) -> str:
    safe = re.sub(r"[^a-z0-9-]", "-", task_id.lower())
    return f"fs-{run_id[:18].replace('_', '-')}-{safe[:30]}-{attempt}"[:63]


def _is_capacity_error(message: str) -> bool:
    lower = message.lower()
    return any(token in lower for token in (
        "resourcelimitexceeded", "insufficientinstancecapacity", "capacity",
        "quota", "supported instance type", "instance type is not supported"))


def _is_oom(message: str) -> bool:
    lower = message.lower()
    return (any(token in lower for token in ("out of memory", "outofmemory", "exitcode 137",
                                              "exit code 137", "memoryerror", "memory limit"))
            or re.search(r"\boom\b", lower) is not None)


def _make_processor(role: str, session: Any, network_config: Any,
                    instance_type: str) -> Any:
    from sagemaker.sklearn.processing import SKLearnProcessor
    return SKLearnProcessor(framework_version=FRAMEWORK_VERSION, role=role,
                            instance_type=instance_type, instance_count=1,
                            sagemaker_session=session, network_config=network_config)


def _submit_one(manifest: dict, task_id: str, *, s3: Any, sm: Any, bucket: str,
                role: str, session: Any, network_config: Any) -> None:
    from sagemaker.processing import ProcessingOutput
    task = manifest["tasks"][task_id]
    spec = task["spec"]
    name = _job_name(manifest["run_id"], task_id, task["attempts"])
    task["job_name"] = name
    task["status"] = "submitting"
    task["tried_instances"].append(spec["instance_type"])
    _save_manifest(s3, bucket, manifest)
    try:
        processor = _make_processor(role, session, network_config, spec["instance_type"])
        processor.run(code=manifest["code_uri"], arguments=["--task-spec", task["spec_uri"]],
                      job_name=name, wait=False,
                      outputs=[ProcessingOutput(output_name="results",
                                                source="/opt/ml/processing/output",
                                                destination=task["output_uri"])])
    except Exception as exc:
        message = str(exc)
        if "already exists" in message.lower():
            try:
                sm.describe_processing_job(ProcessingJobName=name)
                task["status"] = "running"
                _save_manifest(s3, bucket, manifest)
                return
            except Exception:
                # The name is reserved even if Describe is temporarily
                # unavailable. Keep the slot occupied until polling resolves it.
                task["status"] = "submitting"
                _save_manifest(s3, bucket, manifest)
                return
        if _is_capacity_error(message):
            remaining = eligible_instances(spec["estimated_peak_gib"],
                                           excluded=set(task["tried_instances"]))
            if remaining:
                spec["instance_type"] = remaining[0]
                _put_json(s3, task["spec_uri"], spec)
                task["attempts"] += 1
                task["status"] = "pending"
                task["history"].append({"job_name": name, "event": "capacity_rejection",
                                        "reason": message[:500]})
                _save_manifest(s3, bucket, manifest)
                return
            other_active = any(key != task_id and state["status"] in ("running", "submitting")
                               for key, state in manifest["tasks"].items())
            if other_active and task["capacity_rounds"] < 3:
                task["status"] = "deferred"
                task["capacity_rounds"] += 1
                task["history"].append({"job_name": name, "event": "capacity_wait",
                                        "reason": message[:500]})
                _save_manifest(s3, bucket, manifest)
                return
        task["status"] = "failed"
        task["failure_reason"] = f"Submission failed: {message[:500]}"
        _save_manifest(s3, bucket, manifest)
        return
    task["status"] = "running"
    task["submitted_at"] = datetime.now(timezone.utc).isoformat()
    _save_manifest(s3, bucket, manifest)


def _split_oom_task(manifest: dict, task_id: str, s3: Any, bucket: str,
                    reason: str) -> None:
    task = manifest["tasks"][task_id]
    spec = task["spec"]
    columns = spec["feature_columns"]
    depth = spec["split_depth"]
    if len(columns) > 1 and depth < 3:
        midpoint = len(columns) // 2
        for suffix, subset in (("a", columns[:midpoint]), ("b", columns[midpoint:])):
            child = dict(spec)
            child["feature_columns"] = subset
            child["feature_hash"] = _spec_hash(subset)
            child["batch_index"] = str(spec["batch_index"]) + suffix
            child["split_depth"] = depth + 1
            peak = estimate_peak_gib(spec["profile_rows"], len(subset), spec["shared_row_bytes"])
            child["estimated_peak_gib"] = round(peak, 3)
            choices = eligible_instances(peak)
            if not choices:
                task["status"] = "failed"
                task["failure_reason"] = "OOM split produced no schedulable instance"
                return
            child["instance_type"] = choices[0]
            _add_task(s3, bucket, manifest, task_id + suffix, child)
        task["status"] = "superseded"
        task["history"].append({"job_name": task["job_name"], "event": "oom_split",
                                "reason": reason[:500]})
        manifest["books"][spec["book"]]["task_ids"].extend([task_id + "a", task_id + "b"])
        return
    if len(columns) == 1:
        current_ram = INSTANCE_CATALOG[spec["instance_type"]]["memory_gib"]
        choices = eligible_instances(spec["estimated_peak_gib"], min_memory_gib=current_ram+1,
                                     excluded=set(task["tried_instances"]))
        if choices:
            spec["instance_type"] = choices[0]
            _put_json(s3, task["spec_uri"], spec)
            task["attempts"] += 1
            task["status"] = "pending"
            task["history"].append({"job_name": task["job_name"], "event": "oom_larger_instance",
                                    "reason": reason[:500]})
            return
    task["status"] = "failed"
    task["failure_reason"] = f"OOM after retry limit: {reason[:500]}"


def _completed_output(s3: Any, task: dict) -> tuple[bool, str]:
    uri = task["output_uri"] + "resumo.json"
    last_error = "summary not found"
    for _ in range(3):
        try:
            summary = _get_json(s3, uri)
            spec = task["spec"]
            for field in ("run_id", "book", "batch_index", "feature_hash"):
                if summary.get(field) != spec[field]:
                    return False, f"Output identity mismatch: {field}"
            if summary.get("status") not in ("ok", "empty"):
                return False, f"Worker summary status: {summary.get('status')}"
            expected = {"variaveis_excluidas.csv": {"etapa", "variavel"},
                        "metricas.csv": {"etapa", "n_samples"},
                        "variaveis_por_segmento.csv": {"nivel", "variavel"},
                        "variaveis_finais.csv": {"variavel", "tipo"}}
            for filename, fields in expected.items():
                frame = _read_csv(s3, task["output_uri"] + filename)
                needed = fields | {"run_id", "book", "batch_index", "feature_hash"}
                if not needed.issubset(frame.columns):
                    return False, f"Output schema mismatch: {filename}"
                for field in ("run_id", "book", "batch_index", "feature_hash"):
                    if not frame.empty and not frame[field].astype(str).eq(str(spec[field])).all():
                        return False, f"Output row identity mismatch: {filename}/{field}"
            return True, ""
        except Exception as exc:
            last_error = str(exc)
            time.sleep(2)
    return False, last_error


def _poll_jobs(manifest: dict, *, s3: Any, sm: Any, bucket: str) -> int:
    terminal_count = 0
    for task_id, task in list(manifest["tasks"].items()):
        if task["status"] not in ("running", "submitting"):
            continue
        try:
            response = sm.describe_processing_job(ProcessingJobName=task["job_name"])
            task["poll_errors"] = 0
        except Exception as exc:
            task["poll_errors"] += 1
            if task["poll_errors"] >= 5:
                _save_manifest(s3, bucket, manifest)
                raise RuntimeError(f"Cannot safely determine status of {task['job_name']}") from exc
            if task["status"] == "submitting" and task["poll_errors"] >= 3:
                # Reuse the same deterministic name. If the first submission
                # reached SageMaker, the duplicate-name response adopts it.
                task["status"] = "pending"
                task["history"].append({"event": "submission_unknown", "reason": str(exc)[:500]})
            continue
        status = response["ProcessingJobStatus"]
        if status == "Completed":
            terminal_count += 1
            good, reason = _completed_output(s3, task)
            task["status"] = "succeeded" if good else "failed"
            task["failure_reason"] = None if good else reason
            task["ended_at"] = datetime.now(timezone.utc).isoformat()
        elif status in ("Failed", "Stopped"):
            terminal_count += 1
            reason = response.get("FailureReason") or response.get("ExitMessage") or status
            task["ended_at"] = datetime.now(timezone.utc).isoformat()
            if _is_oom(reason):
                _split_oom_task(manifest, task_id, s3, bucket, reason)
            else:
                task["status"] = "failed"
                task["failure_reason"] = reason[:500]
        else:
            task["status"] = "running"
        _save_manifest(s3, bucket, manifest)
    return terminal_count


def _active(manifest: dict) -> list[str]:
    return [key for key, task in manifest["tasks"].items()
            if task["status"] in ("running", "submitting")]


def _pending(manifest: dict) -> list[str]:
    return [key for key, task in manifest["tasks"].items() if task["status"] == "pending"]


def run_jobs(manifest: dict, *, s3: Any, sm: Any, bucket: str, role: str,
             session: Any, network_config: Any, code_path: str) -> dict:
    if not manifest.get("code_uri"):
        local = Path(code_path)
        if not local.is_file():
            raise FileNotFoundError(f"Worker script missing: {local}")
        manifest["code_uri"] = session.upload_data(
            path=str(local.resolve()), bucket=bucket,
            key_prefix=f"fs-results/{manifest['run_id']}/code")
        _save_manifest(s3, bucket, manifest)
    max_concurrent = manifest["config"]["max_concurrent"]
    if not isinstance(max_concurrent, int) or not 1 <= max_concurrent <= 10:
        raise ValueError("max_concurrent must be between 1 and 10")
    while _active(manifest) or _pending(manifest) or any(
            task["status"] == "deferred" for task in manifest["tasks"].values()):
        if _active(manifest):
            terminal_count = _poll_jobs(manifest, s3=s3, sm=sm, bucket=bucket)
            if terminal_count:
                for task in manifest["tasks"].values():
                    if task["status"] == "deferred":
                        task["status"] = "pending"
                        task["tried_instances"] = []
                        task["attempts"] += 1
                _save_manifest(s3, bucket, manifest)
        elif not _pending(manifest):
            for task in manifest["tasks"].values():
                if task["status"] == "deferred":
                    task["status"] = "failed"
                    task["failure_reason"] = "No active job can release Processing capacity"
            _save_manifest(s3, bucket, manifest)
        while len(_active(manifest)) < max_concurrent and _pending(manifest):
            task_id = _pending(manifest)[0]
            _submit_one(manifest, task_id, s3=s3, sm=sm, bucket=bucket,
                        role=role, session=session, network_config=network_config)
        if _active(manifest):
            time.sleep(manifest["config"].get("poll_interval", 30))
    for book, record in manifest["books"].items():
        if record["status"] in ("skipped", "preflight_failed"):
            continue
        leaves = [manifest["tasks"][tid] for tid in record["task_ids"]
                  if manifest["tasks"][tid]["status"] != "superseded"]
        record["status"] = "succeeded" if leaves and all(t["status"] == "succeeded" for t in leaves) else "failed"
        if record["status"] == "failed":
            record["reason"] = "; ".join(t["failure_reason"] or t["status"] for t in leaves
                                           if t["status"] != "succeeded")
    _save_manifest(s3, bucket, manifest)
    return manifest


def _read_csv(s3: Any, uri: str) -> pd.DataFrame:
    bucket, key = _s3_parts(uri)
    payload = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(payload))


def consolidate(manifest: dict, s3: Any, bucket: str, output_dir: str | Path) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    filenames = ["variaveis_excluidas.csv", "metricas.csv", "variaveis_por_segmento.csv"]
    aggregate = {filename: [] for filename in filenames}
    final_rows = []
    for book, record in manifest["books"].items():
        if record["status"] != "succeeded":
            continue
        leaves = [manifest["tasks"][tid] for tid in record["task_ids"]
                  if manifest["tasks"][tid]["status"] != "superseded"]
        if not leaves or any(task["status"] != "succeeded" for task in leaves):
            raise ValueError(f"Incomplete successful book: {book}")
        per_book = {filename: [] for filename in filenames}
        selected = set()
        for task in leaves:
            for filename in filenames:
                frame = _read_csv(s3, task["output_uri"] + filename)
                if not frame.empty:
                    per_book[filename].append(frame)
                    aggregate[filename].append(frame)
            finals = _read_csv(s3, task["output_uri"] + "variaveis_finais.csv")
            if not finals.empty:
                selected.update(finals.loc[finals["tipo"] == "selecionada", "variavel"].dropna())
        book_dir = output / book
        book_dir.mkdir(exist_ok=True)
        for filename, frames in per_book.items():
            if frames:
                pd.concat(frames, ignore_index=True).to_csv(book_dir / filename, index=False)
        for variable in sorted(selected):
            final_rows.append({"run_id": manifest["run_id"], "book": book,
                               "variavel": variable, "tipo": "selecionada",
                               "cross_batch_correlation_checked": len(leaves) == 1})
    for filename, frames in aggregate.items():
        if frames:
            pd.concat(frames, ignore_index=True).to_csv(output / filename, index=False)
    final = pd.DataFrame(final_rows, columns=["run_id", "book", "variavel", "tipo",
                                               "cross_batch_correlation_checked"])
    final.to_csv(output / "variaveis_finais.csv", index=False)
    summary = {"run_id": manifest["run_id"], "sample_table": manifest["sample_table"],
               "sample_count": manifest["sample_count"],
               "book_status": {book: record["status"] for book, record in manifest["books"].items()},
               "selected_feature_rows": len(final),
               "cross_batch_correlation_note": "Pairs in different batches were not compared"}
    (output / "resumo_execucao.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _put_json(s3, f"s3://{bucket}/fs-results/{manifest['run_id']}/resumo_execucao.json", summary)
    return summary


def run_pipeline(*, athena: Any, glue: Any, s3: Any, sm: Any, bucket: str,
                 role: str, session: Any, network_config: Any, code_path: str,
                 output_dir: str | Path, config: dict,
                 resume_run_id: str | None = None) -> dict:
    if resume_run_id:
        manifest = _get_json(s3, _manifest_uri(bucket, resume_run_id))
        if manifest["config"] != config:
            raise ValueError("Resume configuration differs from saved run")
    else:
        manifest = plan_run(athena, glue, s3, bucket, config)
    run_jobs(manifest, s3=s3, sm=sm, bucket=bucket, role=role,
             session=session, network_config=network_config, code_path=code_path)
    return consolidate(manifest, s3, bucket, Path(output_dir) / manifest["run_id"])
