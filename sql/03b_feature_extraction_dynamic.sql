-- ============================================================================
-- File:    03b_feature_extraction_dynamic.sql   (DYNAMIC / 24-48h landmark)
-- Study:   CS-MORT Dynamic (CS-MORT-8 Rebuild)
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_dynamic`
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- Builds the 24-48h LANDMARK features and trajectories for the dynamic model.
-- LEAK DISCIPLINE (audited after build):
--   * Every dynamic feature uses event-level derived tables strictly bounded to
--     (t24, t48]; baseline values for deltas come from cs_features_baseline (0-24h).
--   * Analytic set = patients ALIVE & in ICU at 48h (present_at_48h=1); the
--     landmark-2 model predicts in-hospital death AFTER 48h, conditioned on
--     survival to 48h (handles immortal time).
--   * "new_*" events = present in (t24,t48] AND absent in [intime,t24].
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_dynamic` AS

WITH coh AS (
  SELECT stay_id, subject_id, hadm_id, icu_intime,
    DATETIME_ADD(icu_intime, INTERVAL 24 HOUR) AS t24,
    DATETIME_ADD(icu_intime, INTERVAL 48 HOUR) AS t48,
    present_at_48h, esrd_chronic_dialysis, in_primary_cohort,
    in_hospital_mortality, dead_30d
  FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort`
),
-- 24-48h event-level labs/vitals (strictly t24 < charttime <= t48)
bg48 AS (
  SELECT c.stay_id, MIN(b.lactate) lac_min_2448, MAX(b.lactate) lac_max_2448, MIN(b.ph) ph_min_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.bg` b
    ON c.hadm_id=b.hadm_id AND b.charttime > c.t24 AND b.charttime <= c.t48
  GROUP BY c.stay_id
),
chem48 AS (
  SELECT c.stay_id, MAX(ch.creatinine) creat_max_2448, MAX(ch.bun) bun_max_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.chemistry` ch
    ON c.hadm_id=ch.hadm_id AND ch.charttime > c.t24 AND ch.charttime <= c.t48
  GROUP BY c.stay_id
),
enz48 AS (
  SELECT c.stay_id, MAX(e.alt) alt_max_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.enzyme` e
    ON c.hadm_id=e.hadm_id AND e.charttime > c.t24 AND e.charttime <= c.t48
  GROUP BY c.stay_id
),
vit48 AS (
  SELECT c.stay_id, MIN(v.sbp) sbp_min_2448, MIN(v.mbp) mbp_min_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.vitalsign` v
    ON c.stay_id=v.stay_id AND v.charttime > c.t24 AND v.charttime <= c.t48
  GROUP BY c.stay_id
),
nee48 AS (
  SELECT c.stay_id, MAX(n.norepinephrine_equivalent_dose) nee_max_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.norepinephrine_equivalent_dose` n
    ON c.stay_id=n.stay_id AND n.starttime < c.t48 AND n.endtime > c.t24
  GROUP BY c.stay_id
),
vaso48 AS (
  SELECT c.stay_id,
    ( MAX(CASE WHEN v.norepinephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.epinephrine   IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.dopamine      IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.phenylephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN v.vasopressin   IS NOT NULL THEN 1 ELSE 0 END) ) AS pressor_count_2448,
    MAX(CASE WHEN v.dobutamine IS NOT NULL OR v.milrinone IS NOT NULL THEN 1 ELSE 0 END) AS inotrope_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.vasoactive_agent` v
    ON c.stay_id=v.stay_id AND v.starttime < c.t48 AND v.endtime > c.t24
  GROUP BY c.stay_id
),
rhythm48 AS (
  SELECT c.stay_id,
    MAX(CASE WHEN r.heart_rhythm LIKE 'AF %' OR r.heart_rhythm LIKE 'A Flut%' THEN 1 ELSE 0 END) af_2448,
    MAX(CASE WHEN r.heart_rhythm LIKE 'VT %' OR r.heart_rhythm LIKE 'VF %' OR r.heart_rhythm='Idioventricular' THEN 1 ELSE 0 END) vtvf_2448,
    MAX(CASE WHEN r.heart_rhythm='Asystole' THEN 1 ELSE 0 END) asys_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.rhythm` r
    ON c.subject_id=r.subject_id AND r.charttime > c.t24 AND r.charttime <= c.t48
  GROUP BY c.stay_id
),
arrest_w AS (
  SELECT c.stay_id,
    MAX(CASE WHEN p.starttime BETWEEN c.icu_intime AND c.t24 THEN 1 ELSE 0 END) arrest_024,
    MAX(CASE WHEN p.starttime > c.t24 AND p.starttime <= c.t48 THEN 1 ELSE 0 END) arrest_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_icu.procedureevents` p
    ON c.stay_id=p.stay_id AND p.itemid=225466 AND p.starttime BETWEEN c.icu_intime AND c.t48
  GROUP BY c.stay_id
),
rrt_w AS (
  SELECT c.stay_id,
    MAX(CASE WHEN r.charttime BETWEEN c.icu_intime AND c.t24 THEN 1 ELSE 0 END) rrt_024,
    MAX(CASE WHEN r.charttime > c.t24 AND r.charttime <= c.t48 THEN 1 ELSE 0 END) rrt_2448
  FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.rrt` r
    ON c.stay_id=r.stay_id AND r.dialysis_active=1 AND r.charttime BETWEEN c.icu_intime AND c.t48
  GROUP BY c.stay_id
),
mcs_w AS (
  SELECT stay_id, MAX(CASE WHEN win='024' THEN 1 ELSE 0 END) mcs_024, MAX(CASE WHEN win='2448' THEN 1 ELSE 0 END) mcs_2448
  FROM (
    SELECT c.stay_id, CASE WHEN il.starttime <= c.t24 AND il.endtime >= c.icu_intime THEN '024'
                           WHEN il.starttime <= c.t48 AND il.endtime >= c.t24 THEN '2448' END win
    FROM coh c JOIN `physionet-data.mimiciv_3_1_derived.invasive_line` il
      ON c.stay_id=il.stay_id AND il.line_type IN ('IABP','Impella Line') AND il.starttime <= c.t48
    UNION ALL
    SELECT c.stay_id, CASE WHEN p.starttime BETWEEN c.icu_intime AND c.t24 THEN '024'
                           WHEN p.starttime > c.t24 AND p.starttime <= c.t48 THEN '2448' END
    FROM coh c JOIN `physionet-data.mimiciv_3_1_icu.procedureevents` p
      ON c.stay_id=p.stay_id AND p.itemid IN (229529,229530) AND p.starttime <= c.t48
  ) WHERE win IS NOT NULL GROUP BY stay_id
),
-- SCAI-CSWG stage at 48h (ordinal 1-5 = A-E), worst in (t24,t48].
scai48 AS (
  SELECT c.stay_id,
    CASE
      WHEN vit48.sbp_min_2448<60 OR vit48.mbp_min_2448<50 OR bg48.lac_max_2448>10
           OR (COALESCE(vaso48.pressor_count_2448,0)+COALESCE(vaso48.inotrope_2448,0))>=3
           OR COALESCE(arrest_w.arrest_2448,0)=1 THEN 5
      WHEN ((vit48.sbp_min_2448<90 OR vit48.mbp_min_2448<65) AND bg48.lac_max_2448>5)
           OR (COALESCE(vaso48.pressor_count_2448,0)+COALESCE(vaso48.inotrope_2448,0))>=2
           OR COALESCE(mcs_w.mcs_2448,0)>=1 THEN 4
      WHEN ((vit48.sbp_min_2448<90 OR vit48.mbp_min_2448<65) AND bg48.lac_max_2448>=2)
           OR (COALESCE(vaso48.pressor_count_2448,0)+COALESCE(vaso48.inotrope_2448,0))>=1 THEN 3
      WHEN (vit48.sbp_min_2448<90 OR vit48.mbp_min_2448<65) OR bg48.lac_max_2448>=2
           OR enz48.alt_max_2448>=200 OR bg48.ph_min_2448<7.2 THEN 2
      ELSE 1
    END AS scai_48h_ord
  FROM coh c
  LEFT JOIN vit48 USING(stay_id) LEFT JOIN bg48 USING(stay_id) LEFT JOIN vaso48 USING(stay_id)
  LEFT JOIN enz48 USING(stay_id) LEFT JOIN mcs_w USING(stay_id) LEFT JOIN arrest_w USING(stay_id)
)
SELECT
  c.stay_id, c.present_at_48h, c.in_primary_cohort, c.in_hospital_mortality, c.dead_30d,
  -- 24-48h values
  bg48.lac_min_2448, bg48.lac_max_2448, chem48.creat_max_2448, nee48.nee_max_2448,
  -- TRAJECTORIES (baseline from cs_features_baseline)
  SAFE_DIVIDE(b.lactate_max - bg48.lac_min_2448, NULLIF(b.lactate_max,0)) AS lactate_clearance_frac,
  (bg48.lac_max_2448 - b.lactate_max)        AS delta_lactate_max,
  (COALESCE(nee48.nee_max_2448,0) - COALESCE(b.nee_max,0)) AS delta_nee,
  CASE WHEN COALESCE(nee48.nee_max_2448,0) > COALESCE(b.nee_max,0) THEN 1 ELSE 0 END AS vaso_escalation,
  (chem48.creat_max_2448 - b.creatinine_max) AS delta_creatinine,
  -- NEW-ONSET events (24-48h AND not in 0-24h)
  CASE WHEN COALESCE(rhythm48.af_2448,0)=1   AND COALESCE(b.rhy_af,0)=0 THEN 1 ELSE 0 END AS new_af,
  CASE WHEN COALESCE(rhythm48.vtvf_2448,0)=1 AND COALESCE(b.rhy_vt_vf,0)=0 THEN 1 ELSE 0 END AS new_vt_vf,
  CASE WHEN (COALESCE(rhythm48.asys_2448,0)=1 OR COALESCE(arrest_w.arrest_2448,0)=1)
            AND COALESCE(b.rhy_asystole,0)=0 AND COALESCE(arrest_w.arrest_024,0)=0 THEN 1 ELSE 0 END AS new_arrest,
  CASE WHEN COALESCE(rrt_w.rrt_2448,0)=1 AND COALESCE(rrt_w.rrt_024,0)=0 AND c.esrd_chronic_dialysis=0 THEN 1 ELSE 0 END AS new_rrt_incident,
  CASE WHEN COALESCE(mcs_w.mcs_2448,0)=1 AND COALESCE(mcs_w.mcs_024,0)=0 THEN 1 ELSE 0 END AS new_mcs,
  -- SCAI-CSWG stage at 48h + escalation vs 24h (deterioration; the CSWG signal)
  CASE scai48.scai_48h_ord WHEN 5 THEN 'E' WHEN 4 THEN 'D' WHEN 3 THEN 'C' WHEN 2 THEN 'B' ELSE 'A' END AS scai_cswg_stage_48h,
  CASE WHEN scai48.scai_48h_ord >
            (CASE b.scai_cswg_stage WHEN 'E' THEN 5 WHEN 'D' THEN 4 WHEN 'C' THEN 3 WHEN 'B' THEN 2 ELSE 1 END)
       THEN 1 ELSE 0 END AS scai_escalation
FROM coh c
LEFT JOIN `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline` b USING(stay_id)
LEFT JOIN bg48 USING(stay_id)
LEFT JOIN chem48 USING(stay_id)
LEFT JOIN nee48 USING(stay_id)
LEFT JOIN rhythm48 USING(stay_id)
LEFT JOIN arrest_w USING(stay_id)
LEFT JOIN rrt_w USING(stay_id)
LEFT JOIN mcs_w USING(stay_id)
LEFT JOIN scai48 USING(stay_id);
