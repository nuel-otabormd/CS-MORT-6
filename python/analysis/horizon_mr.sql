-- ============================================================================
-- File:    horizon_mr.sql  (CANONICAL source for the serial-trajectory analysis)
-- Study:   CS-MORT-6 — multi-horizon MIMIC features for 24h/48h re-scoring (Fig 3)
-- Output:  exported to outputs/tables/horizon_mr.csv, read by dynamic_trajectory.py
--          (previously read from an unsaved /tmp/horizon_mr.csv; this is the source).
-- Run:     bq query --project_id=YOUR_PROJECT_ID --use_legacy_sql=false \
--            --max_rows=100000 --format=csv < python/analysis/horizon_mr.sql \
--            > outputs/tables/horizon_mr.csv
-- NOTE:    Most-recent ties order on charttime DESC only; re-runs may differ in ~1
--          of 12,412 rows (descriptive landmark analysis, no effect on conclusions).
-- ----------------------------------------------------------------------------
-- Multi-horizon MOST-RECENT-value extraction: each feature = latest value <= T,
-- for T in {6,12,24,48}h. Leak-safe (charttime <= cutoff), with alive_at_T.
WITH base AS (
  SELECT c.stay_id, c.subject_id, c.hadm_id, c.icu_intime, c.icu_los_hours, c.in_hospital_mortality,
         f.age, f.ami_cs, f.ohca_arrest, w.weight
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` c
  JOIN `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline` f USING(stay_id)
  LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_weight` w USING(stay_id)
  WHERE c.in_primary_cohort=1),
h AS (SELECT b.*, T, DATETIME_ADD(b.icu_intime, INTERVAL T HOUR) AS cutoff FROM base b, UNNEST([6,12,24,48]) AS T),
lac AS (SELECT h.stay_id,h.T, ARRAY_AGG(bg.lactate IGNORE NULLS ORDER BY bg.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] lactate
        FROM h JOIN `physionet-data.mimiciv_3_1_derived.bg` bg ON h.hadm_id=bg.hadm_id AND bg.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
chem AS (SELECT h.stay_id,h.T,
  ARRAY_AGG(ch.bun IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] bun,
  ARRAY_AGG(ch.creatinine IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] creatinine,
  ARRAY_AGG(ch.albumin IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] albumin
  FROM h JOIN `physionet-data.mimiciv_3_1_derived.chemistry` ch ON h.hadm_id=ch.hadm_id AND ch.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
bili AS (SELECT h.stay_id,h.T, ARRAY_AGG(e.bilirubin_total IGNORE NULLS ORDER BY e.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] bilirubin
         FROM h JOIN `physionet-data.mimiciv_3_1_derived.enzyme` e ON h.hadm_id=e.hadm_id AND e.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
rdw AS (SELECT h.stay_id,h.T, ARRAY_AGG(cb.rdw IGNORE NULLS ORDER BY cb.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] rdw
        FROM h JOIN `physionet-data.mimiciv_3_1_derived.complete_blood_count` cb ON h.hadm_id=cb.hadm_id AND cb.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
g AS (SELECT h.stay_id,h.T, ARRAY_AGG(gc.gcs IGNORE NULLS ORDER BY gc.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] gcs
      FROM h JOIN `physionet-data.mimiciv_3_1_derived.gcs` gc ON h.stay_id=gc.stay_id AND gc.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
uo AS (SELECT h.stay_id,h.T, SAFE_DIVIDE(SUM(u.urineoutput), NULLIF(MAX(h.weight),0)*h.T) uo_rate
       FROM h JOIN `physionet-data.mimiciv_3_1_derived.urine_output` u ON h.stay_id=u.stay_id AND u.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2)
SELECT h.stay_id, h.T AS horizon_h, h.in_hospital_mortality,
  CASE WHEN h.icu_los_hours >= h.T THEN 1 ELSE 0 END AS alive_at_T,
  h.age, h.ami_cs, h.ohca_arrest,
  lac.lactate, chem.bun, chem.creatinine, chem.albumin, bili.bilirubin, rdw.rdw, g.gcs, uo.uo_rate
FROM h
LEFT JOIN lac USING(stay_id,T) LEFT JOIN chem USING(stay_id,T) LEFT JOIN bili USING(stay_id,T)
LEFT JOIN rdw USING(stay_id,T) LEFT JOIN g USING(stay_id,T) LEFT JOIN uo USING(stay_id,T)
