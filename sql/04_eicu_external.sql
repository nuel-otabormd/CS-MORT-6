-- ============================================================================
-- File:    04_eicu_external.sql
-- Study:   CS-MORT Dynamic (CS-MORT-8 Rebuild) — EXTERNAL VALIDATION (eICU-CRD)
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_external`
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- PURPOSE
--   Build the eICU external-validation analytic table: one row per CS ICU stay,
--   with the CS-MORT-7 features harmonized to the MIMIC definitions, computed as
--   MOST-RECENT value within the first 24h (offset -60..1440 min), plus the three
--   acid-base markers (lactate / anion gap / bicarbonate) for the variant suite.
--
-- DECISIONS (EO, 2026-06-07):
--   * PRIMARY cohort = diagnosisstring '%cardiogenic shock%' ONLY (standard eICU CS
--     phenotype; honest real-world transportability test; do NOT curate to MIMIC).
--   * SENSITIVITY flag obj_ge1 = diagnosisstring + >=1 objective criterion
--     (SBP<90 or MAP<65 in 24h, lactate>=2, or any vasoactive) to harmonize w/ MIMIC.
--   * PRIMARY externally-deployable model = CS-MORT-7-AG (anion gap substitutes
--     lactate); lactate kept for the lactate variant + complete-case sensitivity.
--   * OHCA harmonized as cardiac-arrest diagnosis + emergency admit source
--     (MIMIC = arrest ICD + ED/emergency admission). Limitation: cannot exclude
--     early in-hospital arrest; documented.
--   * Outcome = hospital mortality (patient.hospitaldischargestatus='Expired').
-- NOTES: eICU times are OFFSETS in minutes from ICU admission (0). age is STRING
--   ('> 89' -> 90). weight = patient.admissionweight (kg).
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_external` AS

WITH cs AS (  -- STEP 1. CS cohort by APACHE diagnosisstring (primary phenotype).
  SELECT DISTINCT patientunitstayid
  FROM `physionet-data.eicu_crd.diagnosis`
  WHERE LOWER(diagnosisstring) LIKE '%cardiogenic shock%'
),
pat AS (  -- STEP 2. Demographics, weight, outcome, OHCA admit-source.
  SELECT p.patientunitstayid,
    CASE WHEN p.age IN ('> 89','>  89') THEN 90.0 ELSE SAFE_CAST(p.age AS FLOAT64) END AS age,
    CASE WHEN p.admissionweight > 0 THEN p.admissionweight END AS weight,
    CASE WHEN p.hospitaldischargestatus = 'Expired' THEN 1 ELSE 0 END AS hosp_mort,
    CASE WHEN p.unitdischargestatus = 'Expired' THEN 1 ELSE 0 END AS icu_mort,
    LOWER(COALESCE(p.unitadmitsource,'')) AS unitadmitsource,
    LOWER(COALESCE(p.hospitaladmitsource,'')) AS hospadmitsource,
    p.unitdischargeoffset
  FROM `physionet-data.eicu_crd.patient` p
  JOIN cs USING (patientunitstayid)
),
arrest AS (  -- cardiac-arrest diagnosis present
  SELECT DISTINCT patientunitstayid, 1 AS arrest_dx
  FROM `physionet-data.eicu_crd.diagnosis` WHERE LOWER(diagnosisstring) LIKE '%cardiac arrest%'
),
-- STEP 3. Most-recent labs within first 24h (offset -60..1440), one value each.
lab_mr AS (
  SELECT patientunitstayid,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%lactate%', labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC LIMIT 1)[SAFE_OFFSET(0)] AS lactate,
    ARRAY_AGG(IF(labname='BUN', labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC LIMIT 1)[SAFE_OFFSET(0)] AS bun,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%anion gap%', labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC LIMIT 1)[SAFE_OFFSET(0)] AS aniongap,
    ARRAY_AGG(IF(labname IN ('bicarbonate','HCO3'), labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC LIMIT 1)[SAFE_OFFSET(0)] AS bicarbonate,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%rdw%', labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC LIMIT 1)[SAFE_OFFSET(0)] AS rdw,
    ARRAY_AGG(IF(LOWER(labname) LIKE '%total bilirubin%', labresult, NULL) IGNORE NULLS ORDER BY labresultoffset DESC LIMIT 1)[SAFE_OFFSET(0)] AS bilirubin
  FROM `physionet-data.eicu_crd.lab`
  WHERE labresultoffset BETWEEN -60 AND 1440
    AND (LOWER(labname) LIKE '%lactate%' OR labname='BUN' OR LOWER(labname) LIKE '%anion gap%'
         OR labname IN ('bicarbonate','HCO3') OR LOWER(labname) LIKE '%rdw%' OR LOWER(labname) LIKE '%total bilirubin%')
  GROUP BY patientunitstayid
),
-- STEP 4. Urine output (first 24h total) -> normalised by weight / 24h in main select.
uo AS (
  SELECT patientunitstayid, SUM(CASE WHEN cellvaluenumeric > 0 THEN cellvaluenumeric ELSE 0 END) AS uo_total_24h
  FROM `physionet-data.eicu_crd.intakeoutput`
  WHERE intakeoutputoffset BETWEEN -60 AND 1440 AND LOWER(celllabel) LIKE '%urine%'
  GROUP BY patientunitstayid
),
-- STEP 5. Objective-criterion components (for the harmonized sensitivity cohort).
hypo AS (
  SELECT DISTINCT patientunitstayid, 1 AS crit_hypotension
  FROM `physionet-data.eicu_crd_derived.pivoted_vital`
  WHERE chartoffset BETWEEN -60 AND 1440
    AND ( (nibp_systolic < 90 AND nibp_systolic > 0) OR (ibp_systolic < 90 AND ibp_systolic > 0)
       OR (nibp_mean < 65 AND nibp_mean > 0) OR (ibp_mean < 65 AND ibp_mean > 0) )
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
  -- OHCA harmonized: arrest dx + emergency admit source
  CASE WHEN ar.arrest_dx = 1 AND (pat.unitadmitsource LIKE '%emergency%' OR pat.hospadmitsource LIKE '%emergency%')
       THEN 1 ELSE 0 END AS ohca_arrest,
  lab_mr.lactate, lab_mr.bun, lab_mr.aniongap, lab_mr.bicarbonate, lab_mr.rdw, lab_mr.bilirubin,
  SAFE_DIVIDE(uo.uo_total_24h, NULLIF(pat.weight,0)*24) AS uo_rate_mlkghr,
  pat.weight,
  -- objective criteria + harmonized-sensitivity flag
  COALESCE(h.crit_hypotension,0) AS crit_hypotension,
  COALESCE(lc.crit_lactate,0)    AS crit_lactate,
  COALESCE(v.crit_vaso,0)        AS crit_vaso,
  CASE WHEN COALESCE(h.crit_hypotension,0)+COALESCE(lc.crit_lactate,0)+COALESCE(v.crit_vaso,0) >= 1
       THEN 1 ELSE 0 END AS obj_ge1
FROM pat
LEFT JOIN arrest  ar USING (patientunitstayid)
LEFT JOIN lab_mr     USING (patientunitstayid)
LEFT JOIN uo         USING (patientunitstayid)
LEFT JOIN hypo    h  USING (patientunitstayid)
LEFT JOIN lac_crit lc USING (patientunitstayid)
LEFT JOIN vaso    v  USING (patientunitstayid)
WHERE pat.age >= 18;
