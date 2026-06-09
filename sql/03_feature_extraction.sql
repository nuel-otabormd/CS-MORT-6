-- ============================================================================
-- File:    03_feature_extraction.sql   (BASELINE / 0-24h window)
-- Study:   CS-MORT Dynamic (CS-MORT-8 Rebuild)
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline`
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- Extracts the full ~70 candidate predictor pool at the BASELINE window for
-- every documented-CS stay in cs_cohort. We start broad; bootstrap stability
-- selection + the parsimony curve decide which survive into the bedside core /
-- echo-enhanced / lactate-free variants. Dynamic (24-48h) deltas are built in
-- 03b_feature_extraction_dynamic.sql.
-- Worst-case summaries per window (max for "bad-high" labs, min for Hb/SBP/SpO2).
-- Leans on derived first_day_* tables (= first ICU day ~ 0-24h); raw only where
-- a concept is absent there (RDW, troponin, pre-admission creatinine).
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline` AS

WITH coh AS (
  SELECT stay_id, subject_id, hadm_id, icu_intime, t24, admittime
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort`
),
-- Troponin T (peak 0-24h) from derived cardiac_marker (subject_id+charttime).
trop AS (
  SELECT c.stay_id, MAX(m.troponin_t) AS troponin_t_max
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.cardiac_marker` m
    ON c.subject_id = m.subject_id AND m.charttime BETWEEN c.icu_intime AND c.t24
  GROUP BY c.stay_id
),
-- RDW (max 0-24h) from DERIVED complete_blood_count (derived-first; not in first_day_lab).
rdw AS (
  SELECT c.stay_id, MAX(cbc.rdw) AS rdw_max
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.complete_blood_count` cbc
    ON c.hadm_id = cbc.hadm_id AND cbc.charttime BETWEEN c.icu_intime AND c.t24 AND cbc.rdw IS NOT NULL
  GROUP BY c.stay_id
),
-- Vasoactives 0-24h: pressor count, inotrope flag (from vasoactive_agent).
vaso AS (
  SELECT c.stay_id,
    ( MAX(CASE WHEN v.norepinephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.epinephrine   IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.dopamine      IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.phenylephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.vasopressin   IS NOT NULL THEN 1 ELSE 0 END) ) AS pressor_count,
    MAX(CASE WHEN v.dobutamine IS NOT NULL OR v.milrinone IS NOT NULL THEN 1 ELSE 0 END) AS inotrope_flag
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.vasoactive_agent` v
    ON c.stay_id = v.stay_id AND v.starttime <= c.t24 AND v.endtime >= c.icu_intime
  GROUP BY c.stay_id
),
-- Max norepinephrine-equivalent dose 0-24h.
nee AS (
  SELECT c.stay_id, MAX(n.norepinephrine_equivalent_dose) AS nee_max
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.norepinephrine_equivalent_dose` n
    ON c.stay_id = n.stay_id AND n.starttime <= c.t24 AND n.endtime >= c.icu_intime
  GROUP BY c.stay_id
),
-- IV loop diuretic 0-24h, in mg IV-FUROSEMIDE-EQUIVALENTS + on-loop flag.
-- Conversion (Ellison & Felker, NEJM 2017; Segar et al, JACC-HF 2024):
--   1 mg bumetanide = 20 mg torsemide = 40 mg IV furosemide = 80 mg oral furosemide.
--   inputevents = IV route only -> IV furosemide x1, IV bumetanide x40. (Oral loop
--   diuretics, in emar/prescriptions, are NOT captured here; add for the decongestion
--   sub-analysis if needed: oral furosemide x0.5, torsemide x2.)
diur AS (
  SELECT c.stay_id,
    SUM(CASE WHEN ie.itemid IN (221794,228340) THEN ie.amount
             WHEN ie.itemid = 229639 THEN ie.amount * 40 ELSE 0 END) AS loop_furos_equiv_mg,
    MAX(1) AS on_iv_loop
  FROM coh c JOIN `physionet-data.mimiciv_3_1_icu.inputevents` ie
    ON c.stay_id = ie.stay_id AND ie.itemid IN (221794,228340,229639)
   AND ie.starttime BETWEEN c.icu_intime AND c.t24
  GROUP BY c.stay_id
),
-- Baseline rhythm flags 0-24h (rhythm table: subject_id + charttime, no stay_id).
rhy AS (
  SELECT c.stay_id,
    MAX(CASE WHEN r.heart_rhythm LIKE 'AF %' OR r.heart_rhythm LIKE 'A Flut%' THEN 1 ELSE 0 END) AS rhy_af,
    MAX(CASE WHEN r.heart_rhythm LIKE 'VT %' OR r.heart_rhythm LIKE 'VF %' OR r.heart_rhythm='Idioventricular' THEN 1 ELSE 0 END) AS rhy_vt_vf,
    MAX(CASE WHEN r.heart_rhythm = 'Asystole' THEN 1 ELSE 0 END) AS rhy_asystole,
    MAX(CASE WHEN r.heart_rhythm LIKE '3rd AV%' THEN 1 ELSE 0 END) AS rhy_chb,
    MAX(CASE WHEN r.heart_rhythm LIKE '%Paced%' THEN 1 ELSE 0 END) AS rhy_paced
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.rhythm` r
    ON c.subject_id = r.subject_id AND r.charttime BETWEEN c.icu_intime AND c.t24
  GROUP BY c.stay_id
),
-- Echo at BASELINE only: from hospital admission through the 24h landmark
-- (admittime..t24). NO post-24h echos (LEAK FIX: 603 stays previously leaked
-- a later-in-stay echo into a baseline feature). LVEF/TAPSE validity-filtered.
echo AS (
  SELECT c.stay_id,
    MIN(CASE WHEN s.measurement='lvef'  AND SAFE_CAST(s.result AS FLOAT64) BETWEEN 5 AND 85  THEN SAFE_CAST(s.result AS FLOAT64) END) AS lvef,
    MIN(CASE WHEN s.measurement='tapse' AND SAFE_CAST(s.result AS FLOAT64) BETWEEN 0.3 AND 4 THEN SAFE_CAST(s.result AS FLOAT64) END) AS tapse,
    MAX(CASE WHEN s.measurement='mitral_regurg'    AND REGEXP_CONTAINS(LOWER(s.result), r'severe|moderate') THEN 1 ELSE 0 END) AS sig_mr,
    MAX(CASE WHEN s.measurement='tricuspid_regurg' AND REGEXP_CONTAINS(LOWER(s.result), r'severe|moderate') THEN 1 ELSE 0 END) AS sig_tr
  FROM coh c
  JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a ON c.hadm_id = a.hadm_id
  JOIN `physionet-data.mimiciv_echo.structured_measurement` s ON c.subject_id = s.subject_id
   AND s.measurement_datetime BETWEEN a.admittime AND c.t24
  GROUP BY c.stay_id
),
-- Pre-admission baseline creatinine = most recent value before admission.
preadm_creat AS (
  SELECT stay_id, valuenum AS preadm_creatinine FROM (
    SELECT c.stay_id, l.valuenum,
           ROW_NUMBER() OVER (PARTITION BY c.stay_id ORDER BY l.charttime DESC) rn
    FROM coh c JOIN `physionet-data.mimiciv_3_1_hosp.labevents` l
      ON c.subject_id = l.subject_id AND l.itemid = 50912
     AND l.valuenum IS NOT NULL AND l.charttime < c.admittime )
  WHERE rn = 1
),
-- KDIGO AKI stage (worst 0-24h) and weight-normalised 24h urine output rate.
aki AS (
  SELECT c.stay_id, MAX(k.aki_stage) AS kdigo_aki_stage
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.kdigo_stages` k
    ON c.stay_id = k.stay_id AND k.charttime BETWEEN c.icu_intime AND c.t24
  GROUP BY c.stay_id
),
-- (UO rate computed in main SELECT as total UO / weight / 24; kdigo_uo.uo_rt_24hr
--  was only ~13% populated, so we normalise first_day_urine_output by weight.)
-- MCS placed WITHIN the 0-24h baseline window (for the SCAI-CSWG stage; not leaky).
mcs24 AS (
  SELECT stay_id, MAX(iabp)+MAX(impella)+MAX(ecmo) AS mcs_24h_count
  FROM (
    SELECT c.stay_id,
      CASE WHEN il.line_type='IABP' THEN 1 ELSE 0 END iabp,
      CASE WHEN il.line_type='Impella Line' THEN 1 ELSE 0 END impella, 0 ecmo
    FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.invasive_line` il
      ON c.stay_id = il.stay_id AND il.starttime <= c.t24 AND il.endtime >= c.icu_intime
    UNION ALL
    SELECT c.stay_id, 0, 0, 1 FROM coh c JOIN `physionet-data.mimiciv_3_1_icu.procedureevents` p
      ON c.stay_id = p.stay_id AND p.itemid IN (229529,229530) AND p.starttime <= c.t24
  ) GROUP BY stay_id
),
-- Resuscitated / out-of-hospital cardiac arrest (the SCAI-E modifier): documented
-- cardiac arrest ICD (I46x / 427.5) WITH acute/ED presentation. A clean baseline
-- predictor, unlike the in-ICU arrest event (which is near-outcome / agonal).
-- Limitation: cannot perfectly exclude an early in-hospital arrest.
arrest AS (
  SELECT DISTINCT c.stay_id, 1 AS ohca_arrest
  FROM coh c
  JOIN `physionet-data.mimiciv_3_1_hosp.diagnoses_icd` dx ON c.hadm_id = dx.hadm_id
  JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a ON c.hadm_id = a.hadm_id
  WHERE (dx.icd_code LIKE 'I46%' OR dx.icd_code = '4275')
    AND (UPPER(a.admission_location) LIKE '%EMERGENCY%' OR UPPER(a.admission_type) LIKE '%EMER%' OR UPPER(a.admission_type)='URGENT')
),
-- Invasive mechanical ventilation within 0-24h (derived ventilation, InvasiveVent).
vent AS (
  SELECT DISTINCT c.stay_id, 1 AS invasive_vent_24h
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.ventilation` v
    ON c.stay_id = v.stay_id AND v.ventilation_status = 'InvasiveVent'
   AND v.starttime <= c.t24 AND v.endtime >= c.icu_intime
)

SELECT
  base.stay_id, base.subject_id, base.hadm_id,
  -- carry key cohort fields/outcomes/flags forward for convenience
  base.age, base.gender,
  -- Etiology: AMI-CS vs non-AMI-CS (primary split); HF-CS = focused non-AMI subgroup.
  -- No "Other" modeling category (valvular/PE/tamponade/post-arrest sit within non-AMI-CS).
  base.has_ami AS ami_cs,
  CASE WHEN base.has_ami = 0 THEN 1 ELSE 0 END AS non_ami_cs,
  CASE WHEN base.has_ami = 0 AND base.has_hf = 1 THEN 1 ELSE 0 END AS hf_cs,
  base.in_primary_cohort, base.in_core_cohort, base.in_documented_only,
  base.in_hospital_mortality, base.dead_30d, base.died_before_24h,
  base.present_at_24h, base.present_at_48h, base.present_at_72h,
  base.esrd_chronic_dialysis, base.sepsis3, base.anchor_year_group,
  -- NOTE: MCS (has_mcs) deliberately NOT a baseline predictor — devices are often
  -- placed >24h (leak). MCS is handled as trajectory (03b) and in the death-or-MCS
  -- composite outcome, computed within proper time windows there.
  -- ===== VITALS (0-24h) =====
  fv.sbp_min, fv.mbp_min, fv.heart_rate_max, fv.spo2_min, fv.temperature_min, fv.resp_rate_max,
  SAFE_DIVIDE(fv.heart_rate_mean, NULLIF(fv.sbp_mean,0)) AS shock_index,  -- mean HR / mean SBP (stable, interpretable)
  -- ===== PERFUSION / BG (0-24h) =====
  fb.lactate_max, fb.ph_min, fb.baseexcess_min, fb.so2_min, fb.pao2fio2ratio_min,
  -- ===== CHEMISTRY / RENAL =====
  fl.bun_max, fl.creatinine_max, SAFE_DIVIDE(fl.bun_max, NULLIF(fl.creatinine_max,0)) AS bun_cr_ratio,
  pc.preadm_creatinine,
  cb.scr_baseline AS baseline_creatinine_est, cb.ckd AS ckd_flag,
  fl.aniongap_max, fl.bicarbonate_min, fl.sodium_min, fl.potassium_max, fl.glucose_max,
  fl.calcium_min, fl.albumin_min,
  -- ===== HEPATIC =====
  fl.ast_max, fl.alt_max, fl.bilirubin_total_max, fl.inr_max,
  -- ===== HEMATOLOGIC =====
  fl.hemoglobin_min, fl.platelets_min, fl.wbc_max,
  SAFE_DIVIDE(fl.abs_neutrophils_max, NULLIF(fl.abs_lymphocytes_min,0)) AS nlr,
  rdw.rdw_max,
  -- ===== CARDIAC BIOMARKERS =====
  trop.troponin_t_max,
  -- ===== RENAL OUTPUT =====
  fu.urineoutput AS urineoutput_24h,
  -- ===== NEURO =====
  fg.gcs_min,
  -- ===== SUPPORT / TREATMENT INTENSITY =====
  COALESCE(vent.invasive_vent_24h,0) AS invasive_vent_24h,
  COALESCE(vaso.pressor_count,0) AS pressor_count,
  COALESCE(vaso.inotrope_flag,0) AS inotrope_flag,
  nee.nee_max,
  COALESCE(diur.on_iv_loop,0) AS on_iv_loop,
  COALESCE(diur.loop_furos_equiv_mg,0) AS loop_furos_equiv_mg,
  -- ===== RHYTHM (baseline) =====
  COALESCE(rhy.rhy_af,0) AS rhy_af, COALESCE(rhy.rhy_vt_vf,0) AS rhy_vt_vf,
  COALESCE(rhy.rhy_asystole,0) AS rhy_asystole, COALESCE(rhy.rhy_chb,0) AS rhy_chb,
  COALESCE(rhy.rhy_paced,0) AS rhy_paced,
  -- ===== ECHO (extended) =====
  echo.lvef, echo.tapse, COALESCE(echo.sig_mr,0) AS sig_mr, COALESCE(echo.sig_tr,0) AS sig_tr,
  -- ===== COMORBIDITY / SEVERITY SCORES =====
  ch.charlson_comorbidity_index,
  ch.diabetes_without_cc + ch.diabetes_with_cc AS dm_any,
  ch.chronic_pulmonary_disease, ch.renal_disease, ch.malignant_cancer,
  fs.sofa AS sofa_24h, ap.apsiii, sa.sapsii, oa.oasis,
  -- ===== RENAL (KDIGO) =====
  COALESCE(aki.kdigo_aki_stage,0) AS kdigo_aki_stage,
  SAFE_DIVIDE(fu.urineoutput, NULLIF(fw.weight,0)*24) AS uo_rate_mlkghr,
  -- ===== EVENTS / DEVICES (baseline 0-24h window) =====
  COALESCE(arrest.ohca_arrest,0) AS ohca_arrest,
  COALESCE(mcs24.mcs_24h_count,0) AS mcs_24h_count,
  -- ===== SCAI-CSWG BASELINE STAGE (Kapur 2022 operationalization;
  --       hierarchical E>D>C>B>A; missing lactate may under-stage) =====
  CASE
    WHEN fv.sbp_min<60 OR fv.mbp_min<50 OR fb.lactate_max>10
         OR (COALESCE(vaso.pressor_count,0)+COALESCE(vaso.inotrope_flag,0))>=3
         OR COALESCE(mcs24.mcs_24h_count,0)>=3 OR COALESCE(arrest.ohca_arrest,0)=1 THEN 'E'
    WHEN ((fv.sbp_min<90 OR fv.mbp_min<65) AND fb.lactate_max>5)
         OR (COALESCE(vaso.pressor_count,0)+COALESCE(vaso.inotrope_flag,0))>=2
         OR COALESCE(mcs24.mcs_24h_count,0)>=1 THEN 'D'
    WHEN ((fv.sbp_min<90 OR fv.mbp_min<65) AND fb.lactate_max>=2)
         OR (COALESCE(vaso.pressor_count,0)+COALESCE(vaso.inotrope_flag,0))>=1 THEN 'C'
    WHEN (fv.sbp_min<90 OR fv.mbp_min<65) OR fb.lactate_max>=2 OR fl.alt_max>=200 OR fb.ph_min<7.2 THEN 'B'
    ELSE 'A'
  END AS scai_cswg_stage
FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` base
LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_vitalsign` fv USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_bg` fb USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_lab` fl USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_gcs` fg USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_urine_output` fu USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_sofa` fs USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.apsiii` ap USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.sapsii` sa USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.oasis` oa USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.charlson` ch ON base.hadm_id = ch.hadm_id
LEFT JOIN `physionet-data.mimiciv_3_1_derived.creatinine_baseline` cb ON base.hadm_id = cb.hadm_id
LEFT JOIN trop USING (stay_id)
LEFT JOIN rdw USING (stay_id)
LEFT JOIN vaso USING (stay_id)
LEFT JOIN nee USING (stay_id)
LEFT JOIN diur USING (stay_id)
LEFT JOIN rhy USING (stay_id)
LEFT JOIN echo USING (stay_id)
LEFT JOIN preadm_creat pc USING (stay_id)
LEFT JOIN aki USING (stay_id)
LEFT JOIN `physionet-data.mimiciv_3_1_derived.first_day_weight` fw USING (stay_id)
LEFT JOIN mcs24 USING (stay_id)
LEFT JOIN arrest USING (stay_id)
LEFT JOIN vent USING (stay_id);
