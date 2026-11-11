-- SCR Stage 0: LIGHTWEIGHT AWS ATHENA ENGINE V3 QUERY PACK
-- Read-only exploration. No full-table aggregates by default.
-- Replace your_database.your_scr_table and ALL placeholders.
-- WARNING: <PARTITION_FILTER> must use the REAL table partition column(s),
-- e.g. ano='2025' AND mes='05', not merely DAT_RFRC_INFO unless it is actually
-- a partition key. Use literal equality on string partition keys.
-- WARNING: Examples assume DAT_RFRC_INFO is DATE. If it is VARCHAR, replace
-- DATE '2025-05-31' with the physical literal, e.g. '2025-05-31'.
-- A hash CPF subset reduces number of groups but by itself DOES NOT prune S3 data.
-- Do not treat sampled results as proof of absence of anomalies in full data.
-- Avoid displaying or exporting raw CPFs; audit summaries only.

-- 0. FREE / LOW-COST METADATA: run independently
SHOW CREATE TABLE your_database.your_scr_table;
-- SHOW PARTITIONS your_database.your_scr_table; -- Hive partitions only, not projected-only
-- DESCRIBE your_database.your_scr_table;

-- 1. CHECK PLAN BEFORE SCANNING (metadata calls possible; no data scan)
EXPLAIN
SELECT DAT_RFRC_INFO, NUM_VERS_RFRC
FROM your_database.your_scr_table
WHERE <PARTITION_FILTER>
  AND DAT_RFRC_INFO = DATE '2025-05-31';
-- Inspect EXPLAIN for pruning of all irrelevant partitions.

-- 2. REFERENCE MONTH CHECK: relatively light if partition filter works.
SELECT
    COUNT(*) AS n_rows,
    MIN(DAT_RFRC_INFO) AS min_reference,
    MAX(DAT_RFRC_INFO) AS max_reference,
    COUNT_IF(DAT_RFRC_INFO <> LAST_DAY_OF_MONTH(DAT_RFRC_INFO)) AS n_not_month_end
FROM your_database.your_scr_table
WHERE <PARTITION_FILTER>
  AND DAT_RFRC_INFO = DATE '2025-05-31';

-- 3. REFERENCE VERSION BREAKDOWN: small GROUP BY; no DISTINCT CPF.
SELECT
    NUM_VERS_RFRC,
    COUNT(*) AS n_rows,
    MIN(DAT_ATUI_RGTO) AS min_update,
    MAX(DAT_ATUI_RGTO) AS max_update,
    MIN(DAT_ULTI_PSST) AS min_processed,
    MAX(DAT_ULTI_PSST) AS max_processed
FROM your_database.your_scr_table
WHERE <PARTITION_FILTER>
  AND DAT_RFRC_INFO = DATE '2025-05-31'
GROUP BY NUM_VERS_RFRC
ORDER BY NUM_VERS_RFRC;

-- 4. APPROXIMATE DISTINCT CPF (lower memory than COUNT(DISTINCT)).
-- An estimate only; not suitable for formal coverage reporting.
SELECT
    COUNT(*) AS n_rows,
    APPROX_DISTINCT(NUM_DOCM_IDEF_PTEV) AS approximate_cpfs,
    APPROX_DISTINCT(COD_MODA_OPER) AS approximate_modalities
FROM your_database.your_scr_table
WHERE <PARTITION_FILTER>
  AND DAT_RFRC_INFO = DATE '2025-05-31';

-- 5. DETERMINISTIC ~0.39% CPF SAMPLE for candidate-key collision checks.
-- Same CPF always gets selected, preserving all of its rows from selected files.
-- Still scans the selected files to compute the hash. If partition pruning fails,
-- this could still scan the entire table (but keeps far fewer groups in memory).
WITH sampled AS (
    SELECT NUM_DOCM_IDEF_PTEV, COD_TIPO_PESS, DAT_RFRC_INFO,
           COD_MODA_OPER, COD_INCA_COGL_ORIG_PTEV,
           NUM_VERS_RFRC, VLR_CRED_AVEN_0_30_DIA
    FROM your_database.your_scr_table
    WHERE <PARTITION_FILTER>
      AND DAT_RFRC_INFO = DATE '2025-05-31'
      AND SUBSTR(
            TO_HEX(MD5(TO_UTF8(CAST(NUM_DOCM_IDEF_PTEV AS VARCHAR)))),
            1, 2
          ) = '00'
), keys AS (
    SELECT NUM_DOCM_IDEF_PTEV, COD_TIPO_PESS, DAT_RFRC_INFO,
           COD_MODA_OPER, COD_INCA_COGL_ORIG_PTEV,
           COUNT(*) AS n_rows,
           MIN(NUM_VERS_RFRC) AS min_version,
           MAX(NUM_VERS_RFRC) AS max_version,
           MIN(VLR_CRED_AVEN_0_30_DIA) AS min_balance,
           MAX(VLR_CRED_AVEN_0_30_DIA) AS max_balance
    FROM sampled
    GROUP BY 1, 2, 3, 4, 5
)
SELECT
    COUNT(*) AS n_sampled_keys,
    COALESCE(SUM(n_rows), 0) AS n_sampled_rows,
    COUNT_IF(n_rows > 1) AS n_colliding_keys,
    COUNT_IF(n_rows > 1 AND min_version <> max_version)
        AS n_collisions_with_different_nonnull_versions,
    COUNT_IF(n_rows > 1 AND min_balance <> max_balance)
        AS n_collisions_with_different_nonnull_balances
FROM keys;
-- NULL-aware comparisons and other financial buckets should be added later.

-- 6. OPTIONAL: SYSTEM file/segment sample for rapid inspection ONLY.
-- Can be biased, may return zero records, and MUST NOT validate uniqueness
-- or historical corrections: some versions/rows may be sampled out.
SELECT DAT_RFRC_INFO, NUM_VERS_RFRC, COD_MODA_OPER
FROM your_database.your_scr_table TABLESAMPLE SYSTEM (1)
WHERE <PARTITION_FILTER>
LIMIT 30;

-- 7. IF UNSCOPED SOURCE READS ARE STILL TOO LARGE:
-- Request/create a tightly scoped, access-controlled CTAS in Parquet.
-- This writes data and requires approval, S3 output location, and a source scan.
-- Not executable until these prerequisites and partition keys are verified.
-- Example skeleton ONLY:
-- CREATE TABLE your_sandbox.scr_stage0_one_month
-- WITH (format = 'PARQUET',
--       external_location = 's3://<authorized-bucket>/<unique-prefix>/') AS
-- SELECT NUM_DOCM_IDEF_PTEV, COD_TIPO_PESS, DAT_RFRC_INFO,
--        COD_MODA_OPER, COD_INCA_COGL_ORIG_PTEV,
--        NUM_VERS_RFRC, DAT_ATUI_RGTO, DAT_ULTI_PSST,
--        VLR_CRED_AVEN_0_30_DIA
-- FROM your_database.your_scr_table
-- WHERE <PARTITION_FILTER>
--   AND DAT_RFRC_INFO = DATE '2025-05-31';
-- In regulated environments, secure S3 encryption, IAM, lifecycle, retention,
-- authorized purpose and restricted access are mandatory review items.
