-- Multi-horizon ("anytime score") feature extraction. For each primary-cohort
-- stay and each horizon T in {6,12,24,48}h, compute worst values STRICTLY within
-- [icu_intime, icu_intime+T] (no leak), plus alive_at_T for landmark conditioning.
WITH base AS (
  SELECT c.stay_id, c.subject_id, c.hadm_id, c.icu_intime, c.icu_los_hours,
         c.in_hospital_mortality, f.age, f.hf_cs, f.ohca_arrest
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` c
  JOIN `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline` f USING (stay_id)
  WHERE c.in_primary_cohort = 1
),
h AS (
  SELECT b.*, T, DATETIME_ADD(b.icu_intime, INTERVAL T HOUR) AS cutoff
  FROM base b, UNNEST([6,12,24,48]) AS T
),
lac AS (SELECT h.stay_id,h.T, MAX(bg.lactate) lactate FROM h JOIN `physionet-data.mimiciv_3_1_derived.bg` bg
        ON h.hadm_id=bg.hadm_id AND bg.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
sbp AS (SELECT h.stay_id,h.T, MIN(v.sbp) sbp FROM h JOIN `physionet-data.mimiciv_3_1_derived.vitalsign` v
        ON h.stay_id=v.stay_id AND v.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
chem AS (SELECT h.stay_id,h.T, MAX(ch.bun) bun, MAX(ch.creatinine) creatinine, MIN(ch.albumin) albumin
         FROM h JOIN `physionet-data.mimiciv_3_1_derived.chemistry` ch
         ON h.hadm_id=ch.hadm_id AND ch.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
bili AS (SELECT h.stay_id,h.T, MAX(e.bilirubin_total) bilirubin FROM h JOIN `physionet-data.mimiciv_3_1_derived.enzyme` e
         ON h.hadm_id=e.hadm_id AND e.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
rdw AS (SELECT h.stay_id,h.T, MAX(cb.rdw) rdw FROM h JOIN `physionet-data.mimiciv_3_1_derived.complete_blood_count` cb
        ON h.hadm_id=cb.hadm_id AND cb.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2),
gcs AS (SELECT h.stay_id,h.T, MIN(g.gcs) gcs FROM h JOIN `physionet-data.mimiciv_3_1_derived.gcs` g
        ON h.stay_id=g.stay_id AND g.charttime BETWEEN h.icu_intime AND h.cutoff GROUP BY 1,2)
SELECT h.stay_id, h.T AS horizon_h, h.in_hospital_mortality,
       CASE WHEN h.icu_los_hours >= h.T THEN 1 ELSE 0 END AS alive_at_T,
       h.age, h.hf_cs, h.ohca_arrest,
       lac.lactate, sbp.sbp, chem.bun, chem.creatinine, chem.albumin, bili.bilirubin, rdw.rdw, gcs.gcs
FROM h
LEFT JOIN lac USING(stay_id,T) LEFT JOIN sbp USING(stay_id,T) LEFT JOIN chem USING(stay_id,T)
LEFT JOIN bili USING(stay_id,T) LEFT JOIN rdw USING(stay_id,T) LEFT JOIN gcs USING(stay_id,T)
