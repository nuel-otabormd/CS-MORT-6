# Input files

Every file the pipeline reads from the data directory (`$CSMORT6_DATA`,
default `data/`), what it contains, and where it comes from. None of these
files are committed: they are derived from MIMIC-IV and eICU-CRD, which are
available to credentialed researchers through PhysioNet under a data use
agreement that does not permit redistribution.

Column lists below are the columns the pipeline actually consumes, so a
reader can confirm a rebuilt file has the right shape before running.

## Extraction tables, built by the queries in `sql/`

The queries write BigQuery tables in the study dataset; each is then
exported to the CSV name given here.

| CSV | Rows | Query | BigQuery table |
|---|---|---|---|
| `cs_features_canonical.csv` | 3,103 | `06_features_canonical_mr.sql` | `cs_features_canonical` |
| `cs_eicu_canonical.csv` | 1,866 | `07_eicu_canonical.sql` | `cs_eicu_canonical` |
| `mimic_demographics.csv` | 3,103 | `08_mimic_demographics.sql` | `cs_mimic_demographics` |
| `scai_components_mimic.csv` | 3,103 | `09_scai_components.sql` | `cs_scai_components_mimic` |
| `eicu_scai_components.csv` | 1,867 | `10_eicu_scai_components.sql` | `cs_eicu_scai_components` |
| `eicu_patient_mapping.csv` | 1,866 | `11_eicu_patient_mapping.sql` | `cs_eicu_patient_mapping` |

`01_cohort_generation.sql`, `03_feature_extraction.sql`,
`03b_feature_extraction_dynamic.sql`, `04_eicu_external.sql` and
`05_eicu_comparators.sql` build the upstream cohort and feature tables that
the canonical queries above draw on. They are included because the canonical
tables cannot be rebuilt without them, not because the pipeline reads their
output directly. The `eicu_scai_components.csv` export carries one stay that
is not in the 1,866-stay cohort; the pipeline's inner join on the cohort
drops it, and the primary-population assertion (n=1,047) in
`06_external_descriptive.py` guards the result.

## Derived extracts

These are narrow projections pulled from the same study dataset for a single
purpose. Each is a straightforward selection over the tables above or over
the source databases; the defining rule is given so the file can be rebuilt.

| CSV | Rows | Contents and rule |
|---|---|---|
| `mimic_exact_lm_flags.csv` | 3,103 | `stay_id, exact_lm24, exact_lm48`. Landmark eligibility from exact timestamps: alive and in the ICU at 24 (48) hours, defined as ICU discharge at or after, and no recorded death at or before, that time. Replaces the whole-hour flags used in the submitted analysis. |
| `mimic_event_time.csv` | 1 | Death-timing distribution (Figure S2) over the development cohort, counted from exact timestamps into the bins named by the column headers. Death-timing panel accompanying Supplementary Figure S1. |
| `eicu_24h_flags.csv` | 1,866 | `patientunitstayid, died_icu_lt24h, in_icu_at_24h`. The eICU landmark equivalent, from unit admission and discharge offsets. |
| `eicu_48h_clean.csv` | 1,866 | 48-hour predictor values for the exploratory reassessment (`lactate48`, `bun48`, `rdw48`, `ag48`, `uo48`) plus `in_icu_48h`, on the same offset convention. |
| `eicu_cmp.csv` | 1,867 | BOS,MA2 comparator inputs in eICU: `bun_max`, `spo2_min`, `sbp_min`, `mech_vent`, `aniongap_max`. Built by `05_eicu_comparators.sql`; the extra row is the header-duplicate artefact of the export and is dropped on merge. |
| `eicu_mcs_published.csv` | 1,130 | Mechanical circulatory support flag used for eICU stage D, restricted to the device interfaces named in the published stage rules (Supplementary Table S2). |
| `mimic_extra_candidates.csv` | 3,103 | Additional candidate predictors offered to the redevelopment sensitivity analyses only: `hemoglobin`, `platelet`, `wbc`, `spo2_min`, `mech_vent`. Never used by the final model. |
| `horizon_mr.csv` | 12,412 | Long-format predictor values by horizon (`horizon_h` in 6, 12, 24, 48 hours) for the availability-by-horizon summary in the Supplementary Table S6 note; the full table remains in the pipeline outputs. One row per stay per horizon. |

## Intermediate written by the pipeline

| CSV | Written by | Contents |
|---|---|---|
| `v2_oof_predictions.csv` | `pipeline/01_develop_landmark.py` | Out-of-fold predictions for the landmark population (`oof_lac`, `oof_ag`, `oof_int`), the fold index, and the outcome. Later steps read it so that internal estimates always come from the same cross-validation, never a refit. It is written into the data directory because it is patient-level and must not be committed. |

The column `score_v2` in that file is the landmark re-derivation card examined
in the point-schedule sensitivity analysis, not the deployed card. Nothing in
the published results is computed from it; the deployed card is built by
`card_score()` in `05_internal_analyses.py` from the printed point schedule.

## feat_baseline_full.csv

The pre-landmark baseline extract for the archived predictor screen
(`pipeline/00_predictor_screen.py`): 4,315 MIMIC-IV ICU stays with documented
cardiogenic shock, 1,537 in-hospital deaths, from 3,479 admissions of 3,192
patients. One row per ICU stay, so stays are not independent observations.
Produced by `sql/01_cohort_generation.sql` and `sql/03_feature_extraction.sql`
without the one-stay-per-patient and landmark restrictions applied later.
Read by the screen only; no landmark or external result depends on it.
