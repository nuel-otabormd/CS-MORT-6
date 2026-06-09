-- =====================================================================
-- 06_features_canonical_mr.sql
-- CANONICAL CS-MORT-6 derivation feature table (MIMIC-IV).
-- Builds ONE durable, reproducible analytic table that the final model and
-- every downstream table/figure read from (replaces the ad-hoc /tmp exports).
--
-- DESIGN DECISIONS (documented for reviewers; code is published):
--  1. MOST-RECENT value up to T=24h (last observation carried forward, LOCF),
--     NOT worst-value. Rationale: the score is intended for SERIAL bedside use
--     and must reflect the patient's CURRENT state (it can improve as the
--     patient improves). Worst-value-to-T is monotonic and cannot fall, so it
--     cannot represent recovery (Steyerberg, Clinical Prediction Models, 2019).
--     All charttime <= t24 => leak-safe (no future information).
--  2. ANION GAP HARMONIZED as sodium - (chloride + bicarbonate), WITHOUT
--     potassium, computed identically here and in eICU (07_*.sql). Rationale:
--     lab-reported anion gap differs by institution convention (some include K);
--     MIMIC's lab-reported value ran ~3 mmol/L higher than eICU's, which would
--     mis-transport a frozen threshold. Computing AG from raw electrolytes makes
--     the cut-points portable (Kraut & Madias, NEJM 2007, anion-gap definition).
--  3. URINE OUTPUT rate = first-24h urine / (weight x ACTUAL observed hours,
--     capped at 24), not / fixed 24. Rationale: dividing a <24h urine total by a
--     fixed 24 underestimates the rate for early-discharge/early-death stays
--     (11.9% of the cohort); using observed hours yields the true average rate.
--  4. Phenotype-source flags (has_cs_icd, has_cs_note_affirm) and sepsis3 are
--     carried so the planned phenotype sensitivity analyses (ICD-only,
--     Sepsis-3-excluded) read from the same canonical table.
-- =====================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_canonical` AS
WITH coh AS (
  SELECT c.stay_id, c.subject_id, c.hadm_id, c.icu_intime,
         DATETIME_ADD(c.icu_intime, INTERVAL 24 HOUR) AS t24,
         c.icu_los_hours, c.in_hospital_mortality, c.dead_30d, c.died_before_24h,
         c.has_cs_icd, c.has_cs_note_affirm, c.sepsis3, c.cs_etiology,
         c.has_ami, c.has_hf, c.present_at_48h, c.anchor_year_group
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` c
  WHERE c.in_primary_cohort = 1
),
-- Most-recent blood-gas values up to t24 (hadm-level): lactate.
bg AS (
  SELECT c.stay_id,
    ARRAY_AGG(b.lactate IGNORE NULLS ORDER BY b.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] AS lactate
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.bg` b
    ON c.hadm_id = b.hadm_id AND b.charttime BETWEEN c.icu_intime AND c.t24
  GROUP BY c.stay_id
),
-- Most-recent chemistry up to t24: components for harmonized anion gap + BUN.
chem AS (
  SELECT c.stay_id,
    ARRAY_AGG(ch.bun         IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] AS bun,
    ARRAY_AGG(ch.sodium      IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] AS sodium,
    ARRAY_AGG(ch.chloride    IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] AS chloride,
    ARRAY_AGG(ch.bicarbonate IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] AS bicarbonate,
    ARRAY_AGG(ch.aniongap    IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] AS aniongap_labreported
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.chemistry` ch
    ON c.hadm_id = ch.hadm_id AND ch.charttime BETWEEN c.icu_intime AND c.t24
  GROUP BY c.stay_id
),
-- Most-recent complete-blood-count up to t24: RDW.
cbc AS (
  SELECT c.stay_id,
    ARRAY_AGG(cb.rdw IGNORE NULLS ORDER BY cb.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] AS rdw
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.complete_blood_count` cb
    ON c.hadm_id = cb.hadm_id AND cb.charttime BETWEEN c.icu_intime AND c.t24
  GROUP BY c.stay_id
),
-- Urine output: first-24h total normalised by weight and ACTUAL observed hours.
uo AS (
  SELECT c.stay_id,
    SAFE_DIVIDE(fu.urineoutput, NULLIF(fw.weight,0) * LEAST(GREATEST(c.icu_los_hours,1.0),24.0)) AS uo_rate_mlkghr
  FROM coh c
  LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_urine_output` fu USING(stay_id)
  LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_weight`       fw USING(stay_id)
),
-- Static / baseline predictors from the already-built baseline table.
base AS (
  SELECT stay_id, age, ohca_arrest
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline`
)
SELECT
  coh.stay_id, coh.subject_id, coh.hadm_id, coh.anchor_year_group,
  -- outcomes
  coh.in_hospital_mortality, coh.dead_30d, coh.died_before_24h,
  -- phenotype-source + sepsis flags (for sensitivity cohorts)
  coh.has_cs_icd, coh.has_cs_note_affirm, coh.sepsis3, coh.cs_etiology, coh.has_ami, coh.has_hf,
  coh.present_at_48h, coh.icu_los_hours,
  -- CS-MORT-6 predictors (most-recent <= 24h)
  base.age, base.ohca_arrest,
  bg.lactate, uo.uo_rate_mlkghr, chem.bun, cbc.rdw,
  -- acid-base variants / harmonised anion gap
  chem.sodium, chem.chloride, chem.bicarbonate,
  (chem.sodium - (chem.chloride + chem.bicarbonate)) AS aniongap_harmonized,  -- Na-Cl-HCO3, no K
  chem.aniongap_labreported,                                                   -- kept for comparison only
  -- missingness indicators (both perfusion variables are MNAR; reported, not necessarily modelled)
  CASE WHEN bg.lactate IS NULL THEN 1 ELSE 0 END AS lactate_missing,
  CASE WHEN uo.uo_rate_mlkghr IS NULL THEN 1 ELSE 0 END AS uo_missing
FROM coh
LEFT JOIN bg   USING(stay_id)
LEFT JOIN chem USING(stay_id)
LEFT JOIN cbc  USING(stay_id)
LEFT JOIN uo   USING(stay_id)
LEFT JOIN base USING(stay_id);
