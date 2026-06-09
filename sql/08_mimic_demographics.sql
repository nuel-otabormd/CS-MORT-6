-- ============================================================================
-- File:    08_mimic_demographics.sql
-- Study:   CS-MORT-6 (CS-MORT-8 Rebuild) — MIMIC demographics for fairness analysis
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_mimic_demographics`
--          (export reproduces outputs/tables/mimic_demographics.csv; one row per
--           primary-cohort index stay)
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- PURPOSE
--   Sex and race grouping for the TRIPOD+AI subgroup (fairness) analysis (Table S5).
--   Previously read from an unsaved /tmp/mimic_demo.csv; this file is the canonical,
--   committed source. Gender from hosp.patients; race from the index admission's
--   hosp.admissions.race, grouped to White / Black / Hispanic / Asian / Other or
--   Unknown. 'SOUTH AMERICAN' and all non-listed values fall to Other/Unknown,
--   reproducing the published grouping (White 1935, Other/Unknown 693, Black 317,
--   Hispanic 84, Asian 74; gender M 1858, F 1245; total 3,103). Verified to match
--   the analysis input exactly.
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_mimic_demographics` AS
SELECT
  c.stay_id,
  p.gender,
  CASE
    WHEN a.race LIKE 'WHITE%'    THEN 'White'
    WHEN a.race LIKE 'BLACK%'    THEN 'Black'
    WHEN a.race LIKE 'HISPANIC%' THEN 'Hispanic'
    WHEN a.race LIKE 'ASIAN%'    THEN 'Asian'
    ELSE 'Other/Unknown'
  END AS race_group
FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` c
JOIN `physionet-data.mimiciv_3_1_hosp.patients`   p USING (subject_id)
JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a USING (hadm_id)
WHERE c.in_primary_cohort = 1;
