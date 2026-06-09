-- ============================================================================
-- File:    05_eicu_comparators.sql
-- Study:   CS-MORT Dynamic — eICU comparator features (BOS,MA2 + CS-MORT-8 + CardShock)
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_comparators`
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- WORST-VALUE (first 24h) components for the published comparator scores, so each
-- is implemented to its ORIGINAL specification (BOS,MA2 uses max BUN / min SpO2 /
-- min SBP / max anion gap; not most-recent). One row per eICU CS stay.
--   BOS,MA2 (Yamga 2023): max BUN>=25, min SpO2<88, min SBP<80, any mech vent,
--                         age>=60, max anion gap>=14   (1 pt each, 0-6).
--   CS-MORT-8 (original): lactate, UO rate, age, BUN, invasive vent, AMI,
--                         pressor count, hemoglobin.
--   CardShock (Harjola 2015): age, confusion(GCS<15), prior MI/CABG, ACS etiology,
--                         LVEF, lactate, eGFR  (LVEF-limited in eICU).
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_comparators` AS
WITH cs AS (
  SELECT DISTINCT patientunitstayid FROM `physionet-data.eicu_crd.diagnosis`
  WHERE LOWER(diagnosisstring) LIKE '%cardiogenic shock%'
),
lab AS (  -- worst-value labs in first 24h
  SELECT patientunitstayid,
    MAX(IF(labname='BUN', labresult, NULL)) AS bun_max,
    MAX(IF(LOWER(labname) LIKE '%anion gap%', labresult, NULL)) AS aniongap_max,
    MAX(IF(LOWER(labname) LIKE '%lactate%', labresult, NULL)) AS lactate_max,
    MAX(IF(labname='creatinine', labresult, NULL)) AS creatinine_max,
    MIN(IF(labname='Hgb', labresult, NULL)) AS hemoglobin_min
  FROM `physionet-data.eicu_crd.lab`
  WHERE labresultoffset BETWEEN -60 AND 1440
  GROUP BY 1
),
vit AS (  -- min SpO2, min systolic BP (nibp or ibp) in first 24h
  SELECT patientunitstayid,
    MIN(CASE WHEN spo2 > 0 THEN spo2 END) AS spo2_min,
    MIN(CASE WHEN nibp_systolic > 0 THEN nibp_systolic END) AS nibp_sbp_min,
    MIN(CASE WHEN ibp_systolic > 0 THEN ibp_systolic END) AS ibp_sbp_min
  FROM `physionet-data.eicu_crd_derived.pivoted_vital`
  WHERE chartoffset BETWEEN -60 AND 1440
  GROUP BY 1
),
vent AS (  -- mechanical ventilation day 1 (apache flag OR treatment record)
  SELECT cs.patientunitstayid,
    CASE WHEN COALESCE(av.ventday1,0)=1 OR t.patientunitstayid IS NOT NULL THEN 1 ELSE 0 END AS mech_vent
  FROM cs
  LEFT JOIN `physionet-data.eicu_crd.apachepredvar` av USING(patientunitstayid)
  LEFT JOIN (SELECT DISTINCT patientunitstayid FROM `physionet-data.eicu_crd.treatment`
             WHERE treatmentoffset BETWEEN -60 AND 1440
               AND (LOWER(treatmentstring) LIKE '%mechanical ventilation%' OR LOWER(treatmentstring) LIKE '%intubation%' OR LOWER(treatmentstring) LIKE '%ventilator%')) t USING(patientunitstayid)
),
press AS (  -- pressor count (distinct agents) in first 24h
  SELECT patientunitstayid,
    ( MAX(CASE WHEN norepinephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN epinephrine   IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN dopamine      IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN phenylephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN vasopressin   IS NOT NULL THEN 1 ELSE 0 END) ) AS pressor_count
  FROM `physionet-data.eicu_crd_derived.pivoted_infusion`
  WHERE chartoffset BETWEEN -60 AND 1440
  GROUP BY 1
),
ami AS (  -- AMI etiology (diagnosisstring MI)
  SELECT DISTINCT patientunitstayid, 1 AS ami_cs
  FROM `physionet-data.eicu_crd.diagnosis`
  WHERE LOWER(diagnosisstring) LIKE '%myocardial infarction%'
),
gcs AS (  -- min GCS first 24h (CardShock confusion proxy)
  SELECT patientunitstayid, MIN(gcs) AS gcs_min
  FROM `physionet-data.eicu_crd_derived.pivoted_gcs`
  WHERE chartoffset BETWEEN -60 AND 1440 GROUP BY 1
)
SELECT
  cs.patientunitstayid,
  lab.bun_max, lab.aniongap_max, lab.lactate_max, lab.creatinine_max, lab.hemoglobin_min,
  vit.spo2_min,
  LEAST(COALESCE(vit.nibp_sbp_min, 9999), COALESCE(vit.ibp_sbp_min, 9999)) AS sbp_min_raw,
  CASE WHEN vit.nibp_sbp_min IS NULL AND vit.ibp_sbp_min IS NULL THEN NULL
       ELSE LEAST(COALESCE(vit.nibp_sbp_min, 9999), COALESCE(vit.ibp_sbp_min, 9999)) END AS sbp_min,
  COALESCE(vent.mech_vent,0) AS mech_vent,
  COALESCE(press.pressor_count,0) AS pressor_count,
  COALESCE(ami.ami_cs,0) AS ami_cs,
  gcs.gcs_min
FROM cs
LEFT JOIN lab   USING(patientunitstayid)
LEFT JOIN vit   USING(patientunitstayid)
LEFT JOIN vent  USING(patientunitstayid)
LEFT JOIN press USING(patientunitstayid)
LEFT JOIN ami   USING(patientunitstayid)
LEFT JOIN gcs   USING(patientunitstayid);
