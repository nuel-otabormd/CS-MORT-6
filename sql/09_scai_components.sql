-- ============================================================================
-- File:    09_scai_components.sql
-- Study:   CS-MORT-6 — MIMIC SCAI-stage components for the within-stage figure (Fig 2)
-- Output:  `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_scai_components_mimic`
--          (export reproduces outputs/tables/scai_components_mimic.csv)
-- Author:  Emmanuel Otabor, MD
-- ----------------------------------------------------------------------------
-- PURPOSE
--   Components for the escalation-anchored SCAI re-operationalization (Figure 2,
--   scai_rebuild.py / eicu_withinstage.py). Previously read from an unsaved
--   /tmp/scai_comp.csv; this is the canonical source. Every column is a straight
--   projection of cs_features_baseline (built by 03_feature_extraction.sql), so
--   no new computation is introduced. Verified to reproduce the committed CSV
--   exactly (3,103 rows, 0 cell differences).
--     scai_old = scai_cswg_stage (the original BP-nadir staging, which over-assigns
--     stage E to 49% of the cohort); the escalation-anchored 'scai_new' is computed
--     in scai_rebuild.py from pressor_count + inotrope_flag + mcs_24h_count +
--     ohca_arrest + lactate_max + sbp_min/mbp_min, reducing stage E to 27%.
-- ============================================================================
CREATE OR REPLACE TABLE `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_scai_components_mimic` AS
SELECT
  b.stay_id,
  b.pressor_count,
  b.inotrope_flag,
  b.mcs_24h_count,
  b.ohca_arrest,
  b.lactate_max,
  b.sbp_min,
  b.mbp_min,
  b.scai_cswg_stage AS scai_old
FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_baseline` b
JOIN `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_cohort` c USING (stay_id)
WHERE c.in_primary_cohort = 1;
