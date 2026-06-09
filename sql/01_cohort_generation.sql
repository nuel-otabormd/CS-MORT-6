-- ============================================================================
-- File:    01_cohort_generation.sql
-- Study:   CS-MORT Dynamic (CS-MORT-8 Rebuild)
-- Database: MIMIC-IV v3.1 via BigQuery (project physionet-data)
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort`
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- PURPOSE
--   Build the analytic cohort of adult ICU patients with cardiogenic shock (CS),
--   using an ALL-ICU, DOCUMENTATION-ANCHORED phenotype confirmed by objective
--   hypoperfusion/hypotension criteria. Every filter is a labelled step so the
--   CONSORT flow is transparent, honest, and 100% reproducible.
--
-- DESIGN DECISIONS (rationale in REBUILD_LOG.md / analysis_plan.md):
--   * ALL adult ICUs (not CCU-only): CCU-only previously discarded ~61% of CS
--     and the CVICU device population.
--   * DOCUMENTATION-ANCHORED: ICD R57.0/785.51 OR a TRUE, CURRENT, AFFIRMED
--     "cardiogenic shock" mention in the discharge note. Note affirmation is
--     determined by a reproducible medspaCy/ConText classifier (python/
--     01b_note_cs_classifier.py -> table note_cs_affirm), which performs
--     mention-level negation/historical/hypothetical/family/uncertainty
--     detection. This REPLACES whole-note regex, which over-aggregated (a
--     single differential mention killed an otherwise-affirmed note) and lost
--     genuine tamponade/PE/post-arrest/post-cardiotomy CS.
--   * OBJECTIVE CRITERION graded on SCAI-CSWG axes (hypotension, hypoperfusion,
--     treatment intensity); used to confirm shock physiology, NOT as a hard
--     SCAI stage gate (avoids circularity when SCAI-CSWG is a comparator).
--   * NO arbitrary LOS>=8h exclusion (it silently dropped the sickest early
--     deaths). Minimal LOS>=4h to allow an early-window assessment; landmark
--     windows handle immortal time downstream; early deaths reported.
--   * SEPSIS is a covariate + sensitivity cohort, NOT an exclusion.
--   * Index (first qualifying) ICU stay per patient retained.
-- ============================================================================

CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` AS

WITH
-- STEP 1. All adult ICU stays (denominator).
all_icu AS (
  SELECT
    i.stay_id, i.subject_id, i.hadm_id,
    i.first_careunit,
    i.intime  AS icu_intime,
    i.outtime AS icu_outtime,
    DATETIME_DIFF(i.outtime, i.intime, HOUR) AS icu_los_hours,
    DATETIME_ADD(i.intime, INTERVAL 24 HOUR) AS t24,
    ag.age, p.gender, p.dod, p.anchor_year_group,
    adm.admittime, adm.dischtime, adm.deathtime, adm.hospital_expire_flag
  FROM `physionet-data.mimiciv_3_1_icu.icustays` i
  JOIN `physionet-data.mimiciv_3_1_derived.age` ag ON i.hadm_id = ag.hadm_id
  JOIN `physionet-data.mimiciv_3_1_hosp.patients` p ON i.subject_id = p.subject_id
  JOIN `physionet-data.mimiciv_3_1_hosp.admissions` adm ON i.hadm_id = adm.hadm_id
  WHERE ag.age >= 18
),

-- STEP 2a. CS by ICD-9 785.51 / ICD-10 R57.0 (clean).
cs_icd AS (
  SELECT DISTINCT hadm_id, 1 AS has_cs_icd
  FROM `physionet-data.mimiciv_3_1_hosp.diagnoses_icd`
  WHERE icd_code IN ('78551','R570')
),
-- STEP 2b. CS by discharge note, AFFIRMED current mention from the medspaCy/
--          ConText classifier (python/01b_note_cs_classifier.py).
cs_note AS (
  SELECT hadm_id, has_cs_note_affirm, n_affirm_mentions, n_total_mentions
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.note_cs_affirm`
),

-- STEP 3. Cardiac diagnoses (etiology + descriptor). Both ICD-9 and ICD-10.
cardiac_dx AS (
  SELECT hadm_id,
    MAX(CASE WHEN icd_code LIKE '410%' OR icd_code LIKE 'I21%' THEN 1 ELSE 0 END) AS has_ami,
    MAX(CASE WHEN icd_code LIKE '428%' OR icd_code LIKE 'I50%' THEN 1 ELSE 0 END) AS has_hf,
    MAX(CASE WHEN icd_code LIKE '425%' OR icd_code LIKE 'I42%' THEN 1 ELSE 0 END) AS has_cmp,
    MAX(CASE WHEN icd_code LIKE '424%' OR icd_code LIKE 'I34%' OR icd_code LIKE 'I35%'
                  OR icd_code LIKE 'I05%' OR icd_code LIKE 'I06%' OR icd_code LIKE 'I08%' THEN 1 ELSE 0 END) AS has_valve
  FROM `physionet-data.mimiciv_3_1_hosp.diagnoses_icd`
  GROUP BY hadm_id
),

-- STEP 4. OBJECTIVE shock criteria within first 24h (SCAI-CSWG axes).
crit_hypotension AS (
  SELECT DISTINCT a.stay_id FROM all_icu a
  JOIN `physionet-data.mimiciv_3_1_icu.chartevents` c
    ON a.stay_id = c.stay_id AND c.charttime BETWEEN a.icu_intime AND a.t24
   AND ( (c.itemid IN (220050,220179) AND c.valuenum < 90 AND c.valuenum > 0)
      OR (c.itemid IN (220052,220181) AND c.valuenum < 65 AND c.valuenum > 0) )
),
crit_lactate AS (
  SELECT DISTINCT a.stay_id FROM all_icu a
  JOIN `physionet-data.mimiciv_3_1_hosp.labevents` l
    ON a.hadm_id = l.hadm_id AND l.itemid = 50813
   AND l.charttime BETWEEN a.icu_intime AND a.t24 AND l.valuenum >= 2.0
),
crit_treatment AS (
  SELECT DISTINCT a.stay_id FROM all_icu a
  JOIN `physionet-data.mimiciv_3_1_derived.vasoactive_agent` v
    ON a.stay_id = v.stay_id AND v.starttime <= a.t24 AND v.endtime >= a.icu_intime
   AND ( v.norepinephrine IS NOT NULL OR v.epinephrine IS NOT NULL OR v.dopamine IS NOT NULL
      OR v.phenylephrine IS NOT NULL OR v.vasopressin IS NOT NULL
      OR v.dobutamine IS NOT NULL OR v.milrinone IS NOT NULL )
),

-- STEP 5. Exclusion / covariate / outcome flags.
esrd AS (
  SELECT DISTINCT hadm_id, 1 AS esrd_chronic_dialysis
  FROM `physionet-data.mimiciv_3_1_hosp.diagnoses_icd`
  WHERE icd_code IN ('5856','V4511','N186','Z992') OR icd_code LIKE 'V56%' OR icd_code LIKE 'Z491%'
),
sepsis AS (SELECT DISTINCT stay_id, 1 AS sepsis3 FROM `physionet-data.mimiciv_3_1_derived.sepsis3`),
mcs AS (
  SELECT stay_id, MAX(iabp) AS mcs_iabp, MAX(impella) AS mcs_impella, MAX(ecmo) AS mcs_ecmo
  FROM (
    SELECT stay_id, CASE WHEN line_type='IABP' THEN 1 ELSE 0 END iabp,
           CASE WHEN line_type='Impella Line' THEN 1 ELSE 0 END impella, 0 ecmo
    FROM `physionet-data.mimiciv_3_1_derived.invasive_line`
    UNION ALL
    SELECT stay_id, CASE WHEN itemid IN (220120,227980) THEN 1 ELSE 0 END,
           CASE WHEN itemid IN (229897,224318,228148,228149,224314) THEN 1 ELSE 0 END, 0
    FROM `physionet-data.mimiciv_3_1_icu.chartevents` WHERE itemid IN (220120,227980,229897,224318,228148,228149,224314)
    UNION ALL
    SELECT stay_id, 0,0,1 FROM `physionet-data.mimiciv_3_1_icu.procedureevents` WHERE itemid IN (229529,229530)
    UNION ALL
    SELECT stay_id, 0,0,1 FROM `physionet-data.mimiciv_3_1_icu.chartevents` WHERE itemid IN (224660,228193)
  )
  GROUP BY stay_id
),

-- STEP 6. Assemble per-stay record.
assembled AS (
  SELECT
    a.*,
    COALESCE(ci.has_cs_icd,0)         AS has_cs_icd,
    COALESCE(cn.has_cs_note_affirm,0) AS has_cs_note_affirm,
    COALESCE(cn.n_affirm_mentions,0)  AS n_affirm_mentions,
    COALESCE(cd.has_ami,0)  AS has_ami,  COALESCE(cd.has_hf,0)   AS has_hf,
    COALESCE(cd.has_cmp,0)  AS has_cmp,  COALESCE(cd.has_valve,0) AS has_valve,
    CASE WHEN ch.stay_id IS NOT NULL THEN 1 ELSE 0 END AS crit_hypotension,
    CASE WHEN cl.stay_id IS NOT NULL THEN 1 ELSE 0 END AS crit_lactate,
    CASE WHEN ct.stay_id IS NOT NULL THEN 1 ELSE 0 END AS crit_treatment,
    COALESCE(es.esrd_chronic_dialysis,0) AS esrd_chronic_dialysis,
    CASE WHEN sp.stay_id IS NOT NULL THEN 1 ELSE 0 END AS sepsis3,
    CASE WHEN m.stay_id IS NOT NULL AND (m.mcs_iabp=1 OR m.mcs_impella=1 OR m.mcs_ecmo=1) THEN 1 ELSE 0 END AS has_mcs,
    COALESCE(m.mcs_iabp,0) AS mcs_iabp, COALESCE(m.mcs_impella,0) AS mcs_impella, COALESCE(m.mcs_ecmo,0) AS mcs_ecmo
  FROM all_icu a
  LEFT JOIN cs_icd  ci ON a.hadm_id = ci.hadm_id
  LEFT JOIN cs_note cn ON a.hadm_id = cn.hadm_id
  LEFT JOIN cardiac_dx cd ON a.hadm_id = cd.hadm_id
  LEFT JOIN crit_hypotension ch ON a.stay_id = ch.stay_id
  LEFT JOIN crit_lactate cl ON a.stay_id = cl.stay_id
  LEFT JOIN crit_treatment ct ON a.stay_id = ct.stay_id
  LEFT JOIN esrd es ON a.hadm_id = es.hadm_id
  LEFT JOIN sepsis sp ON a.stay_id = sp.stay_id
  LEFT JOIN mcs m ON a.stay_id = m.stay_id
),

-- STEP 7. Composite phenotype, outcomes, landmark flags, index-stay marker.
derived AS (
  SELECT *,
    -- Documentation: ICD OR ConText-affirmed note (mention-level, accurate).
    CASE WHEN has_cs_icd = 1 OR has_cs_note_affirm = 1 THEN 1 ELSE 0 END AS cs_documented,
    (crit_hypotension + crit_lactate + crit_treatment) AS n_objective,
    CASE WHEN has_ami=1 OR has_hf=1 OR has_cmp=1 OR has_valve=1 THEN 1 ELSE 0 END AS has_cardiac_dx,
    CASE WHEN has_ami=1 THEN 'AMI-CS'
         WHEN has_hf=1 OR has_cmp=1 THEN 'HF-CS'
         WHEN has_valve=1 THEN 'Valvular-CS'
         ELSE 'Other/Unspecified' END AS cs_etiology,
    hospital_expire_flag AS in_hospital_mortality,
    CASE WHEN dod IS NOT NULL AND DATE_DIFF(dod, DATE(admittime), DAY) <= 30 THEN 1 ELSE 0 END AS dead_30d,
    CASE WHEN icu_los_hours >= 24 THEN 1 ELSE 0 END AS present_at_24h,
    CASE WHEN icu_los_hours >= 48 THEN 1 ELSE 0 END AS present_at_48h,
    CASE WHEN icu_los_hours >= 72 THEN 1 ELSE 0 END AS present_at_72h,
    CASE WHEN hospital_expire_flag = 1 AND deathtime IS NOT NULL
              AND DATETIME_DIFF(deathtime, icu_intime, HOUR) < 24 THEN 1 ELSE 0 END AS died_before_24h,
    -- Index (first QUALIFYING) ICU stay per patient. Prioritise stays meeting
    -- BOTH documentation AND >=1 objective criterion, then documented-only, then
    -- earliest. (Bug fix: ordering by documentation alone lost 59 patients whose
    -- earliest documented stay lacked objective criteria but a later one qualified.)
    ROW_NUMBER() OVER (
      PARTITION BY subject_id
      ORDER BY
        CASE WHEN (has_cs_icd=1 OR has_cs_note_affirm=1)
                  AND (crit_hypotension + crit_lactate + crit_treatment) >= 1 THEN 0
             WHEN (has_cs_icd=1 OR has_cs_note_affirm=1) THEN 1
             ELSE 2 END,
        icu_intime
    ) AS stay_rank
  FROM assembled
)

-- STEP 8. Final universe = documented CS, with cohort membership flags.
--   NO LOS entry restriction: survival time is never an inclusion criterion
--   (avoids immortal-time / early-death bias; short-LOS CS = the highest-risk
--   patients, 50-80% mortality). Survival is handled at the LANDMARK stage
--   (early-window scores everyone; 24h/48h landmarks condition on survival).
--   `los_ge_4h` is retained only as a descriptor / feature-window helper.
SELECT
  d.*,
  CASE WHEN icu_los_hours >= 4 THEN 1 ELSE 0 END AS los_ge_4h,
  CASE WHEN cs_documented = 1 AND n_objective >= 1 AND stay_rank = 1
       THEN 1 ELSE 0 END AS in_primary_cohort,
  CASE WHEN cs_documented = 1 AND n_objective >= 2 AND stay_rank = 1
       THEN 1 ELSE 0 END AS in_core_cohort,
  CASE WHEN cs_documented = 1 AND stay_rank = 1
       THEN 1 ELSE 0 END AS in_documented_only
FROM derived d
WHERE d.cs_documented = 1;
