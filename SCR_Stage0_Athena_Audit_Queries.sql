-- SCR representation learning POC / Stage 0
-- SQL dialect: Amazon Athena engine v3 (Trino-based)
-- Based on SCR metadata screenshots and confirmed monthly consultation cadence.
-- All source-table placeholders (<...>) must be replaced with real Athena names.
-- Athena typically exposes lower-case column identifiers; unquoted names are case-insensitive.
-- DATE-like source fields are shown as DATE in the original dictionary but must be
-- checked against the physical Athena schema before scanning data.
-- DATE fields formatted as non-ISO VARCHAR need explicit date_parse/try conversion.
-- DO NOT assume DAT_ATUI_RGTO or DAT_ULTI_PSST is the time the bank knew a record.
-- NUM_VERS_RFRC is described as a reference BASE version: not necessarily a record version.
-- Avoid exporting CPF-level output outside authorized environments.
-- Run scoped reference ranges first if the source is a large/partitioned table.

-- A00. Discover physical SCR columns and types (edit database/table names).
SELECT column_name, data_type, ordinal_position, is_nullable
FROM information_schema.columns
WHERE table_schema = '<DATABASE>' AND table_name = '<TABLE_NAME>'
ORDER BY ordinal_position;

-- A01. Overall range and month-end validation.
WITH typed AS (
    SELECT TRY_CAST(DAT_RFRC_INFO AS DATE) AS reference_date,
           DAT_RFRC_INFO AS reference_raw
    FROM <SCR_TABLE>
)
SELECT MIN(reference_date) AS min_reference,
       MAX(reference_date) AS max_reference,
       COUNT(*) AS n_rows,
       COUNT(DISTINCT reference_date) AS n_reference_months,
       SUM(CASE WHEN reference_raw IS NULL THEN 1 ELSE 0 END) AS null_raw_reference,
       SUM(CASE WHEN reference_raw IS NOT NULL AND reference_date IS NULL THEN 1 ELSE 0 END) AS invalid_reference_cast,
       SUM(CASE WHEN reference_date IS NOT NULL
                 AND reference_date <> last_day_of_month(reference_date)
                THEN 1 ELSE 0 END) AS not_month_end
FROM typed;

-- A02. Rows and distinct CPF identifiers by reference month.
SELECT TRY_CAST(DAT_RFRC_INFO AS DATE) AS reference_date,
       COUNT(*) AS n_rows,
       COUNT(DISTINCT NUM_DOCM_IDEF_PTEV) AS n_documents,
       COUNT(DISTINCT COD_MODA_OPER) AS n_modalities,
       COUNT(DISTINCT COD_INCA_COGL_ORIG_PTEV) AS n_institutions
FROM <SCR_TABLE>
GROUP BY 1
ORDER BY reference_date DESC;

-- A03. Candidate logical-key collision summary, without returning sensitive identifiers.
-- Additional dimensions (base version, reference archive, validity, reversal) may explain collisions.
WITH candidate_keys AS (
    SELECT NUM_DOCM_IDEF_PTEV, COD_TIPO_PESS, DAT_RFRC_INFO,
           COD_MODA_OPER, COD_INCA_COGL_ORIG_PTEV,
           COUNT(*) AS n_rows,
           COUNT(DISTINCT NUM_VERS_RFRC) AS n_versions,
           COUNT(DISTINCT NUM_DAT_RFRC_ARQU) AS n_archive_refs
    FROM <SCR_TABLE>
    GROUP BY 1, 2, 3, 4, 5
)
SELECT COUNT(*) AS n_candidate_keys,
       SUM(n_rows) AS n_source_rows,
       SUM(CASE WHEN n_rows > 1 THEN 1 ELSE 0 END) AS n_colliding_keys,
       SUM(CASE WHEN n_rows > 1 THEN n_rows - 1 ELSE 0 END) AS n_extra_rows,
       SUM(CASE WHEN n_versions > 1 THEN 1 ELSE 0 END) AS n_multi_version_keys,
       SUM(CASE WHEN n_archive_refs > 1 THEN 1 ELSE 0 END) AS n_multi_archive_ref_keys,
       MAX(n_rows) AS max_rows_per_candidate_key
FROM candidate_keys;

-- A04. Debug collision examples; run ONLY in restricted workspace.
SELECT NUM_DOCM_IDEF_PTEV, COD_TIPO_PESS, DAT_RFRC_INFO,
       COD_MODA_OPER, COD_INCA_COGL_ORIG_PTEV,
       COUNT(*) AS n_rows,
       COUNT(DISTINCT NUM_VERS_RFRC) AS n_versions,
       COUNT(DISTINCT NUM_DAT_RFRC_ARQU) AS n_archive_refs,
       MIN(DAT_ATUI_RGTO) AS min_update,
       MAX(DAT_ATUI_RGTO) AS max_update
FROM <SCR_TABLE>
GROUP BY 1,2,3,4,5
HAVING COUNT(*) > 1
ORDER BY n_rows DESC
LIMIT 100;

-- A05. Reference-base versions and date fields by reference month.
SELECT TRY_CAST(DAT_RFRC_INFO AS DATE) AS reference_date,
       NUM_VERS_RFRC,
       COUNT(*) AS n_rows,
       COUNT(DISTINCT NUM_DOCM_IDEF_PTEV) AS n_documents,
       MIN(TRY_CAST(DAT_ATUI_RGTO AS DATE)) AS min_record_update,
       MAX(TRY_CAST(DAT_ATUI_RGTO AS DATE)) AS max_record_update,
       MIN(TRY_CAST(DAT_ULTI_PSST AS DATE)) AS min_last_processed,
       MAX(TRY_CAST(DAT_ULTI_PSST AS DATE)) AS max_last_processed
FROM <SCR_TABLE>
GROUP BY 1, 2
ORDER BY reference_date DESC, NUM_VERS_RFRC DESC;

-- A06. Do repeated candidate keys have differing balance values or versions?
-- Only examines the 0-30-day maturity bucket; generalize after key is confirmed.
WITH repeated AS (
    SELECT NUM_DOCM_IDEF_PTEV, COD_TIPO_PESS, DAT_RFRC_INFO,
           COD_MODA_OPER, COD_INCA_COGL_ORIG_PTEV,
           COUNT(*) AS n_rows,
           COUNT(DISTINCT NUM_VERS_RFRC) AS n_versions,
           COUNT(DISTINCT CAST(VLR_CRED_AVEN_0_30_DIA AS VARCHAR)) AS n_distinct_balances,
           COUNT(DISTINCT CAST(DAT_ATUI_RGTO AS VARCHAR)) AS n_update_dates
    FROM <SCR_TABLE>
    GROUP BY 1,2,3,4,5
    HAVING COUNT(*) > 1
)
SELECT COUNT(*) AS n_repeated_keys,
       SUM(CASE WHEN n_versions > 1 THEN 1 ELSE 0 END) AS n_keys_multi_version,
       SUM(CASE WHEN n_distinct_balances > 1 THEN 1 ELSE 0 END) AS n_keys_different_balance,
       SUM(CASE WHEN n_update_dates > 1 THEN 1 ELSE 0 END) AS n_keys_different_update_dates
FROM repeated;
-- Important: no repeated keys does NOT prove records were never overwritten.

-- A07. Compare internal DATE columns with reference months.
-- This is a DIAGNOSTIC only; not a consultation / availability lag calculation.
WITH typed AS (
    SELECT TRY_CAST(DAT_RFRC_INFO AS DATE) AS ref_date,
           TRY_CAST(DAT_ATUI_RGTO AS DATE) AS update_date,
           TRY_CAST(DAT_ULTI_PSST AS DATE) AS processed_date
    FROM <SCR_TABLE>
)
SELECT date_diff('month', date_trunc('month', ref_date),
                date_trunc('month', update_date)) AS update_lag_months,
       COUNT(*) AS n_rows,
       MIN(ref_date) AS min_reference,
       MAX(ref_date) AS max_reference
FROM typed
WHERE ref_date IS NOT NULL AND update_date IS NOT NULL
GROUP BY 1
ORDER BY update_lag_months;

-- A08. Investigate archival reference, validity, reversal flag and processing fields.
-- Meanings and reversal codes must be confirmed with source owners.
SELECT NUM_VERS_RFRC,
       NUM_DAT_RFRC_ARQU,
       IND_ESTO_SIST,
       COUNT(*) AS n_rows,
       MIN(TRY_CAST(DAT_VIGE AS DATE)) AS min_validity_date,
       MAX(TRY_CAST(DAT_VIGE AS DATE)) AS max_validity_date,
       MIN(TRY_CAST(DAT_ULTI_PSST AS DATE)) AS min_processing_date,
       MAX(TRY_CAST(DAT_ULTI_PSST AS DATE)) AS max_processing_date
FROM <SCR_TABLE>
GROUP BY 1,2,3
ORDER BY n_rows DESC
LIMIT 200;

-- B09. TEMPLATE ONLY: monthly consultation coverage and actual run dates.
-- Map the following unverified fields: person_id, batch_id,
-- consultation_at, status, ingestion_at. Batch completion may be a separate source.
SELECT date_trunc('month', consultation_at) AS consultation_month,
       COUNT(*) AS n_consultation_events,
       COUNT(DISTINCT person_id) AS n_consulted_people,
       COUNT(DISTINCT batch_id) AS n_batches,
       MIN(consultation_at) AS earliest_consultation,
       MAX(consultation_at) AS latest_consultation,
       MIN(ingestion_at) AS earliest_ingestion,
       MAX(ingestion_at) AS latest_ingestion,
       status,
       COUNT(DISTINCT person_id) AS people_by_status
FROM <CONSULTATION_LOG>
GROUP BY 1, status
ORDER BY consultation_month DESC, status;

-- B10. TEMPLATE ONLY: verify M-2 using ACTUAL consultation/report linkage.
-- Each row must have a legitimate link between the specific report and request.
-- Replace consultation_at, reference_date, ingestion_at, report_id with real fields.
WITH observed AS (
    SELECT report_id, consultation_at, ingestion_at, reference_date,
           date_diff('month', date_trunc('month', CAST(reference_date AS DATE)),
                     date_trunc('month', CAST(consultation_at AS DATE))) AS lag_months
    FROM <REPORT_CONSULTATION_LINK>
)
SELECT lag_months,
       COUNT(*) AS n_reports,
       MIN(consultation_at) AS first_consultation,
       MAX(consultation_at) AS last_consultation,
       SUM(CASE WHEN ingestion_at > consultation_at THEN 1 ELSE 0 END) AS ingested_after_consultation
FROM observed
GROUP BY 1
ORDER BY lag_months;

-- B11. TEMPLATE ONLY: measure actual batch-to-ingestion delay.
-- Confirm time zones; the 24-hour threshold here is illustrative, NOT a bank SLA.
SELECT batch_id,
       CAST(batch_started_at AS DATE) AS batch_date,
       batch_started_at,
       batch_finished_at,
       ingestion_completed_at,
       date_diff('hour', batch_finished_at, ingestion_completed_at) AS ingestion_delay_hours,
       CASE
           WHEN ingestion_completed_at IS NULL THEN 'missing_ingestion'
           WHEN ingestion_completed_at > batch_finished_at + INTERVAL '24' HOUR THEN 'over_24h'
           WHEN ingestion_completed_at < batch_finished_at THEN 'review_clock_or_stage_semantics'
           ELSE 'within_24h'
       END AS delay_bucket
FROM <BATCH_LOG>
ORDER BY batch_started_at DESC
LIMIT 200;

-- B12. TEMPLATE ONLY: availability relative to applications.
-- This returns status counts, not a valid source-record join by itself.
-- Map person_id between systems with a time-valid, authorized identity mapping.
-- A real report->record link + permission check are additionally required.
WITH eligible_consultations AS (
    SELECT a.application_id,
           c.consultation_at,
           c.ingestion_at,
           c.report_id,
           ROW_NUMBER() OVER (
             PARTITION BY a.application_id
             ORDER BY c.ingestion_at DESC, c.consultation_at DESC
           ) AS recency_rank
    FROM <APPLICATIONS> a
    JOIN <CONSULTATION_LOG> c
      ON a.person_id = c.person_id
     AND c.consultation_at < a.application_time
     AND c.ingestion_at < a.application_time
     -- Add verified: authorization, permitted purpose, report success,
     -- actual record-version availability, and any corrected-version logic.
)
SELECT COUNT(*) AS applications_with_preapplication_consultations
FROM eligible_consultations
WHERE recency_rank = 1;

-- Questions unanswered by SCR alone:
-- * Whether the bank consulted every eligible CPF in a given month.
-- * The actual historical availability timestamp of each report/version.
-- * Whether previous values were overwritten rather than preserved.
-- * Whether historical authorization and permitted purpose were valid.
-- * Whether DAT_ATUI_RGTO / DAT_ULTI_PSST represent source updates or bank availability.
