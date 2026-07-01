-- ============================================================================
-- File:    supplementary_analyses/sql/exports.sql
-- Study:   CS-MORT-6 — table exports for the supplementary analyses and figures
-- Project: physionet-data (source) + YOUR_PROJECT_ID (your working project)
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- PURPOSE
--   The supplementary analyses (python/*.py, r/render_figures.R) read flat CSVs
--   from data/. This file documents the BigQuery exports that populate data/.
--   Replace YOUR_PROJECT_ID with your Google Cloud project. Run each block with
--   the bq CLI:
--
--     bq query --use_legacy_sql=false --format=csv --max_rows=100000 \
--       '<SELECT>' > data/<name>.csv
--
--   The canonical tables here are the persisted outputs of the main pipeline
--   (sql/06_features_canonical_mr.sql, 07_eicu_canonical.sql, 08_mimic_demographics.sql,
--    09_scai_components.sql, 10_eicu_scai_components.sql). Build those first.
--
-- DATA-USE NOTE: the resulting CSVs are patient-level PhysioNet data. Do NOT
--   commit them (see .gitignore: supplementary_analyses/data/*.csv is excluded).
-- ============================================================================

-- [1] -> data/cs_features_canonical.csv   (MIMIC-IV features + outcomes + missingness flags, n=3103)
SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_canonical`;

-- [2] -> data/scai_components_mimic.csv    (MIMIC-IV SCAI-stage components, n=3103)
SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_scai_components_mimic`;

-- [3] -> data/mimic_demographics.csv       (gender, race_group for the subgroup analysis)
SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_mimic_demographics`;

-- [4] -> data/cs_eicu_canonical.csv        (eICU external features + outcomes, n=1866)
SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_canonical`;

-- [5] -> data/eicu_scai_components.csv     (eICU SCAI components: vaso_count, inotrope_flag, mcs, arrest_dx)
SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_scai_components`;

-- [6] -> data/eicu_mcs_published.csv       (mechanical circulatory support in-window; IABP/Impella/ECMO,
--        excluding "intraaortic balloon pump removal" rows, to match the main within-stage staging; n=347)
SELECT DISTINCT patientunitstayid, 1 AS mcs
FROM `physionet-data.eicu_crd.treatment`
WHERE treatmentoffset BETWEEN -60 AND 1440
  AND ( LOWER(treatmentstring) LIKE '%intraaortic balloon%'
     OR LOWER(treatmentstring) LIKE '%impella%'
     OR LOWER(treatmentstring) LIKE '%ecmo%' )
  AND LOWER(treatmentstring) NOT LIKE '%removal%';

-- ----------------------------------------------------------------------------
-- FIGURE-INPUT CSVs (from the main pipeline, not exported here):
--   data/cal_mimic6.csv, cal_eicu6.csv, dca_eicu_cm6.csv
--       -> patient-level predicted probabilities from python/analysis/csmort6_final.py
--          (cal_* -> p,y or p_ag,p_lac,y ; dca -> p_ag,bm,y). Patient-level: do NOT commit.
--   data/fig4_withinstage.csv, fig5_trajectory.csv
--       -> aggregate; copy from outputs/tables_aggregate/. Shareable.
-- ============================================================================
