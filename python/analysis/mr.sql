-- Most-recent-value (LOCF) features at the 24h reference: each lab/vital = its
-- latest non-null value within [icu_intime, t24]. Time-series-correct (the score
-- reflects current state and can improve). Statics/treatments joined from baseline.
WITH coh AS (
  SELECT stay_id, subject_id, hadm_id, icu_intime, DATETIME_ADD(icu_intime, INTERVAL 24 HOUR) AS t24
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` WHERE in_primary_cohort=1),
bg AS (SELECT c.stay_id,
  ARRAY_AGG(b.lactate IGNORE NULLS ORDER BY b.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] lactate,
  ARRAY_AGG(b.ph      IGNORE NULLS ORDER BY b.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] ph
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.bg` b ON c.hadm_id=b.hadm_id AND b.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1),
chem AS (SELECT c.stay_id,
  ARRAY_AGG(ch.bun         IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] bun,
  ARRAY_AGG(ch.creatinine  IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] creatinine,
  ARRAY_AGG(ch.albumin     IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] albumin,
  ARRAY_AGG(ch.sodium      IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] sodium,
  ARRAY_AGG(ch.potassium   IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] potassium,
  ARRAY_AGG(ch.glucose     IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] glucose,
  ARRAY_AGG(ch.calcium     IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] calcium,
  ARRAY_AGG(ch.bicarbonate IGNORE NULLS ORDER BY ch.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] bicarbonate
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.chemistry` ch ON c.hadm_id=ch.hadm_id AND ch.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1),
enz AS (SELECT c.stay_id,
  ARRAY_AGG(e.ast IGNORE NULLS ORDER BY e.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] ast,
  ARRAY_AGG(e.bilirubin_total IGNORE NULLS ORDER BY e.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] bilirubin
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.enzyme` e ON c.hadm_id=e.hadm_id AND e.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1),
cbc AS (SELECT c.stay_id,
  ARRAY_AGG(cb.hemoglobin IGNORE NULLS ORDER BY cb.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] hemoglobin,
  ARRAY_AGG(cb.platelet   IGNORE NULLS ORDER BY cb.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] platelets,
  ARRAY_AGG(cb.wbc        IGNORE NULLS ORDER BY cb.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] wbc,
  ARRAY_AGG(cb.rdw        IGNORE NULLS ORDER BY cb.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] rdw
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.complete_blood_count` cb ON c.hadm_id=cb.hadm_id AND cb.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1),
coag AS (SELECT c.stay_id, ARRAY_AGG(co.inr IGNORE NULLS ORDER BY co.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] inr
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.coagulation` co ON c.hadm_id=co.hadm_id AND co.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1),
cm AS (SELECT c.stay_id, ARRAY_AGG(m.troponin_t IGNORE NULLS ORDER BY m.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] troponin
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.cardiac_marker` m ON c.subject_id=m.subject_id AND m.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1),
vit AS (SELECT c.stay_id,
  ARRAY_AGG(v.sbp        IGNORE NULLS ORDER BY v.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] sbp,
  ARRAY_AGG(v.mbp        IGNORE NULLS ORDER BY v.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] mbp,
  ARRAY_AGG(v.heart_rate IGNORE NULLS ORDER BY v.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] heart_rate
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.vitalsign` v ON c.stay_id=v.stay_id AND v.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1),
g AS (SELECT c.stay_id, ARRAY_AGG(gc.gcs IGNORE NULLS ORDER BY gc.charttime DESC LIMIT 1)[SAFE_OFFSET(0)] gcs
 FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.gcs` gc ON c.stay_id=gc.stay_id AND gc.charttime BETWEEN c.icu_intime AND c.t24 GROUP BY 1)
SELECT c.stay_id, f.in_hospital_mortality,
  f.age, f.gender, f.hf_cs, f.ami_cs, f.ohca_arrest, f.invasive_vent_24h, f.pressor_count, f.inotrope_flag,
  f.on_iv_loop, f.uo_rate_mlkghr, f.kdigo_aki_stage, f.dm_any, f.chronic_pulmonary_disease, f.malignant_cancer, f.ckd_flag,
  CASE WHEN bg.lactate IS NULL THEN 1 ELSE 0 END AS lactate_missing,
  bg.lactate, bg.ph, chem.bun, chem.creatinine, chem.albumin, chem.sodium, chem.potassium, chem.glucose, chem.calcium,
  chem.bicarbonate, enz.ast, enz.bilirubin, cbc.hemoglobin, cbc.platelets, cbc.wbc, cbc.rdw, coag.inr, cm.troponin,
  vit.sbp, vit.mbp, vit.heart_rate, g.gcs
FROM coh c
JOIN `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline` f USING(stay_id)
LEFT JOIN bg USING(stay_id) LEFT JOIN chem USING(stay_id) LEFT JOIN enz USING(stay_id) LEFT JOIN cbc USING(stay_id)
LEFT JOIN coag USING(stay_id) LEFT JOIN cm USING(stay_id) LEFT JOIN vit USING(stay_id) LEFT JOIN g USING(stay_id)
