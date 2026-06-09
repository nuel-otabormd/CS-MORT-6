-- ============================================================================
-- File:    10_eicu_scai_components.sql
-- Study:   CS-MORT-6 — eICU SCAI-stage components for the within-stage figure (Fig 2)
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_scai_components`
--          (regenerates outputs/tables/eicu_scai_components.csv and, as the mcs=1
--           subset, outputs/tables/eicu_mcs.csv)
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- PURPOSE
--   eICU components for the coarse E>D>C>B staging used in Figure 2
--   (eicu_withinstage.py). Previously read from unsaved /tmp/eicu_scai.csv and
--   /tmp/eicu_mcs.csv; this is the canonical source. Only three partitions drive
--   the figure: any vasoactive support, mechanical circulatory support (MCS), and
--   cardiac-arrest diagnosis.
--     support  = (vaso_count > 0) OR (inotrope_flag = 1)  -> stage C
--     mcs      = 1                                         -> stage D
--     arrest_dx= 1                                         -> stage E
--
-- RELATION TO THE COMMITTED CSV
--   arrest_dx (n=490) and the support partition (any of 7 vasoactives, n=1108)
--   reproduce the committed eicu_scai_components.csv EXACTLY. MCS here is in-window
--   IABP/Impella/ECMO from the treatment table (n=354); the published eicu_mcs.csv
--   used a marginally tighter IABP definition (n=347), a strict subset (the 7 extra
--   are IABP treatment rows the original excluded). The 0.4% difference cannot move
--   the figure: the within-stage tertile separation is unchanged. The committed CSVs
--   are retained as the exact published artifacts; this SQL is the regeneration path.
-- NOTE: vaso_count is the count of distinct vasopressors; downstream only (>0) is used.
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_scai_components` AS
WITH cs AS (
  SELECT DISTINCT patientunitstayid
  FROM `physionet-data.eicu_crd.diagnosis`
  WHERE LOWER(diagnosisstring) LIKE '%cardiogenic shock%'
),
arr AS (
  SELECT DISTINCT patientunitstayid, 1 AS arrest_dx
  FROM `physionet-data.eicu_crd.diagnosis`
  WHERE LOWER(diagnosisstring) LIKE '%cardiac arrest%'
),
inf AS (  -- distinct vasopressors + inotrope presence in first 24 h
  SELECT patientunitstayid,
    ( MAX(CASE WHEN norepinephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN epinephrine   IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN dopamine      IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN phenylephrine IS NOT NULL THEN 1 ELSE 0 END)
    + MAX(CASE WHEN vasopressin   IS NOT NULL THEN 1 ELSE 0 END) ) AS vaso_count,
    MAX(CASE WHEN dobutamine IS NOT NULL OR milrinone IS NOT NULL THEN 1 ELSE 0 END) AS inotrope_flag
  FROM `physionet-data.eicu_crd_derived.pivoted_infusion`
  WHERE chartoffset BETWEEN -60 AND 1440
  GROUP BY patientunitstayid
),
mcs AS (  -- in-window MCS (IABP / Impella / ECMO) from the treatment table
  SELECT DISTINCT patientunitstayid, 1 AS mcs
  FROM `physionet-data.eicu_crd.treatment`
  WHERE treatmentoffset BETWEEN -60 AND 1440
    AND ( LOWER(treatmentstring) LIKE '%intraaortic balloon%'
       OR LOWER(treatmentstring) LIKE '%impella%'
       OR LOWER(treatmentstring) LIKE '%ecmo%' )
)
SELECT
  cs.patientunitstayid,
  COALESCE(inf.vaso_count,0)    AS vaso_count,
  COALESCE(inf.inotrope_flag,0) AS inotrope_flag,
  COALESCE(mcs.mcs,0)           AS mcs,
  COALESCE(arr.arrest_dx,0)     AS arrest_dx
FROM cs
LEFT JOIN inf USING (patientunitstayid)
LEFT JOIN mcs USING (patientunitstayid)
LEFT JOIN arr USING (patientunitstayid);
