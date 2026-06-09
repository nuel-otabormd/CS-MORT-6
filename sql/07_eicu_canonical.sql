-- ============================================================================
-- File:    07_eicu_canonical.sql
-- Study:   CS-MORT-6 (CS-MORT-8 Rebuild) — CANONICAL eICU EXTERNAL-VALIDATION TABLE
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_canonical`
--          (export reproduces outputs/tables/cs_eicu_canonical.csv)
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- PURPOSE
--   Single authoritative query for the eICU external-validation analytic table:
--   one row per cardiogenic-shock ICU stay with the six CS-MORT-6 predictors
--   harmonized to the MIMIC definitions, the acid-base markers, the HARMONIZED
--   anion gap (computed identically to MIMIC as sodium - (chloride + bicarbonate)),
--   the objective-criterion flags, and the outcome. This supersedes the earlier
--   04_eicu_external.sql, which (a) used stale CS-MORT-7 naming, (b) did not emit
--   sodium / chloride / bicarb / aniongap_harmonized, so it never reproduced the
--   analysis CSV. This file closes that gap.
--
-- DETERMINISM AND RELATION TO THE COMMITTED CSV
--   Every most-recent (LOCF) lab uses ORDER BY labresultoffset DESC, labid DESC.
--   The secondary key (labid, unique) pins the tie-break so repeated runs of this
--   query are bit-identical (verified). The committed analysis artifact
--   outputs/tables/cs_eicu_canonical.csv was produced by an earlier ad-hoc export
--   that ordered on labresultoffset only; that tie-break was nondeterministic and
--   differs from this query in ~26/1866 rows, all genuine same-offset ties between
--   duplicate 'bicarbonate' and 'HCO3' entries (median |delta| 1.8 in harmonized
--   anion gap). The effect on results is within tie-break noise: external AUROC is
--   0.748 (anion gap) for the committed CSV versus 0.749 for a fresh deterministic
--   run, and 0.757 (lactate) for both; calibration slope 0.95 and mortality 0.345
--   are unchanged. The committed CSV is retained as the exact published artifact;
--   this SQL is the deterministic, reproducible source of record going forward.
--
-- DEFINITIONS (harmonized to MIMIC 06_features_canonical_mr.sql)
--   * Cohort = APACHE diagnosisstring LIKE '%cardiogenic shock%' (primary eICU CS
--     phenotype; not curated to MIMIC, an honest transportability test).
--   * Window = first 24 h, labresultoffset / chartoffset / intakeoutputoffset in
--     [-60, 1440] minutes from ICU admission. Each lab = most-recent value in window.
--   * Anion gap HARMONIZED = sodium - (chloride + bicarbonate), WITHOUT potassium,
--     computed identically here and in MIMIC so frozen cut-points transport
--     (Kraut & Madias, NEJM 2007). lab-reported aniongap is kept for reference only.
--   * Urine output rate = first-24 h urine / (admission weight x 24). NOTE: MIMIC
--     divides by ACTUAL observed hours capped at 24; eICU lacks a clean per-hour
--     window so a fixed 24 h denominator is used. This residual harmonization
--     difference is documented in the manuscript; urine output is the weakest
--     predictor and the external AUROC is unchanged under plausible rescaling.
--   * OHCA harmonized = cardiac-arrest diagnosis + emergency admit source.
--   * obj_ge1 (harmonized-sensitivity flag) = >=1 of SBP<90 or MAP<65, lactate>=2,
--     any vasoactive, within the window.
--   * Outcome = in-hospital mortality (patient.hospitaldischargestatus='Expired').
-- NOTES: eICU age is a STRING ('> 89' -> 90). weight = patient.admissionweight (kg).
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_canonical` AS

WITH cs AS (  -- STEP 1. CS cohort by APACHE diagnosisstring (primary phenotype).
  SELECT DISTINCT patientunitstayid
  FROM `physionet-data.eicu_crd.diagnosis`
  WHERE LOWER(diagnosisstring) LIKE '%cardiogenic shock%'
),
pat AS (  -- STEP 2. Demographics, weight, outcome, admit-source for OHCA.
  SELECT p.patientunitstayid,
    CASE WHEN p.age IN ('> 89','>  89') THEN 90.0 ELSE SAFE_CAST(p.age AS FLOAT64) END AS age,
    CASE WHEN p.admissionweight > 0 THEN p.admissionweight END AS weight,
    CASE WHEN p.hospitaldischargestatus = 'Expired' THEN 1 ELSE 0 END AS hosp_mort,
    CASE WHEN p.unitdischargestatus    = 'Expired' THEN 1 ELSE 0 END AS icu_mort,
    LOWER(COALESCE(p.unitadmitsource,''))     AS unitadmitsource,
    LOWER(COALESCE(p.hospitaladmitsource,'')) AS hospadmitsource
  FROM `physionet-data.eicu_crd.patient` p
  JOIN cs USING (patientunitstayid)
),
arrest AS (  -- cardiac-arrest diagnosis present
  SELECT DISTINCT patientunitstayid, 1 AS arrest_dx
  FROM `physionet-data.eicu_crd.diagnosis`
  WHERE LOWER(diagnosisstring) LIKE '%cardiac arrest%'
),
-- STEP 3. Most-recent labs within first 24 h, DETERMINISTIC tie-break (labid DESC).
lab_mr AS (
  SELECT patientunitstayid,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%lactate%',        labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS lactate,
    ARRAY_AGG(IF(labname = 'BUN',                        labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS bun,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%anion gap%',      labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS aniongap,
    ARRAY_AGG(IF(labname IN ('bicarbonate','HCO3'),      labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS bicarbonate,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%rdw%',            labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS rdw,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%total bilirubin%',labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS bilirubin,
    ARRAY_AGG(IF(labname = 'sodium',                     labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS sodium,
    ARRAY_AGG(IF(labname = 'chloride',                   labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS chloride,
    ARRAY_AGG(IF(labname IN ('bicarbonate','HCO3'),      labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC, labid DESC LIMIT 1)[SAFE_OFFSET(0)] AS bicarb
  FROM `physionet-data.eicu_crd.lab`
  WHERE labresultoffset BETWEEN -60 AND 1440
  GROUP BY patientunitstayid
),
-- STEP 4. Urine output (first 24 h total) -> rate per weight / fixed 24 h (see header).
uo AS (
  SELECT patientunitstayid, SUM(CASE WHEN cellvaluenumeric > 0 THEN cellvaluenumeric ELSE 0 END) AS uo_total_24h
  FROM `physionet-data.eicu_crd.intakeoutput`
  WHERE intakeoutputoffset BETWEEN -60 AND 1440 AND LOWER(celllabel) LIKE '%urine%'
  GROUP BY patientunitstayid
),
-- STEP 5. Objective-criterion components (harmonized-sensitivity cohort).
hypo AS (
  SELECT DISTINCT patientunitstayid, 1 AS crit_hypotension
  FROM `physionet-data.eicu_crd_derived.pivoted_vital`
  WHERE chartoffset BETWEEN -60 AND 1440
    AND ( (nibp_systolic < 90 AND nibp_systolic > 0) OR (ibp_systolic < 90 AND ibp_systolic > 0)
       OR (nibp_mean    < 65 AND nibp_mean    > 0) OR (ibp_mean    < 65 AND ibp_mean    > 0) )
),
lac_crit AS (
  SELECT DISTINCT patientunitstayid, 1 AS crit_lactate
  FROM `physionet-data.eicu_crd.lab`
  WHERE LOWER(labname) LIKE '%lactate%' AND labresultoffset BETWEEN -60 AND 1440 AND labresult >= 2.0
),
vaso AS (
  SELECT DISTINCT patientunitstayid, 1 AS crit_vaso
  FROM `physionet-data.eicu_crd_derived.pivoted_infusion`
  WHERE chartoffset BETWEEN -60 AND 1440
    AND (norepinephrine IS NOT NULL OR epinephrine IS NOT NULL OR dopamine IS NOT NULL
         OR phenylephrine IS NOT NULL OR vasopressin IS NOT NULL OR dobutamine IS NOT NULL OR milrinone IS NOT NULL)
)
SELECT
  pat.patientunitstayid,
  pat.hosp_mort, pat.icu_mort,
  pat.age,
  CASE WHEN ar.arrest_dx = 1 AND (pat.unitadmitsource LIKE '%emergency%' OR pat.hospadmitsource LIKE '%emergency%')
       THEN 1 ELSE 0 END AS ohca_arrest,
  lab_mr.lactate, lab_mr.bun, lab_mr.aniongap, lab_mr.bicarbonate, lab_mr.rdw, lab_mr.bilirubin,
  SAFE_DIVIDE(uo.uo_total_24h, NULLIF(pat.weight,0)*24) AS uo_rate_mlkghr,
  pat.weight,
  COALESCE(h.crit_hypotension,0) AS crit_hypotension,
  COALESCE(lc.crit_lactate,0)    AS crit_lactate,
  COALESCE(v.crit_vaso,0)        AS crit_vaso,
  CASE WHEN COALESCE(h.crit_hypotension,0)+COALESCE(lc.crit_lactate,0)+COALESCE(v.crit_vaso,0) >= 1
       THEN 1 ELSE 0 END AS obj_ge1,
  lab_mr.sodium, lab_mr.chloride, lab_mr.bicarb,
  (lab_mr.sodium - (lab_mr.chloride + lab_mr.bicarb)) AS aniongap_harmonized
FROM pat
LEFT JOIN arrest   ar USING (patientunitstayid)
LEFT JOIN lab_mr      USING (patientunitstayid)
LEFT JOIN uo          USING (patientunitstayid)
LEFT JOIN hypo     h  USING (patientunitstayid)
LEFT JOIN lac_crit lc USING (patientunitstayid)
LEFT JOIN vaso     v  USING (patientunitstayid)
WHERE pat.age >= 18;
