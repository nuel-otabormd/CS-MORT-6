# `python/analysis/` — development & analysis scripts

This directory holds the model-development and analysis scripts for CS-MORT-6. They fall into two groups.

## Canonical, reproducible scripts (read from `outputs/tables/`)
These reproduce the manuscript's numbers end-to-end from the persisted canonical tables built by `sql/06–10`:
- `csmort6_final.py`, `csmort6_results.py`, `csmort6_tail.py` — final model, performance tables, calibration/DCA inputs.
- `eicu_withinstage.py` — within-SCAI-stage tertiles (Figure 4).
- `reaudit.py` — integrity re-audit (no duplication, no leakage, reproduces headline numbers).
- `csmort6_figs.R`, `figs6.R`, `headline_figures.R`, `figure1_consort.R` — figures at 300 DPI.

Supplementary analyses and figures live in `../../supplementary_analyses/` (self-contained).

## Development / exploratory scripts (read from `/tmp/`)
The remaining scripts (`bakeoff.py`, `firstpass.py`, `bestsubset.py`, `selection.py`, `cutpoints.py`, `critique.py`, `ag_test.py`, `integer_score.py`, etc.) are the development record of model selection, cut-point derivation, and sensitivity checks. They read **patient-level scratch exports from `/tmp/`** created during development. These are convenience exports, not the canonical tables; they are patient-level PhysioNet data and are **not** committed (PhysioNet DUA; see `.gitignore`).

To regenerate the `/tmp/` scratch files, export the corresponding BigQuery selects (replace `YOUR_PROJECT_ID`). The main mappings:

| Scratch file | Contents | Source |
|---|---|---|
| `/tmp/feat_mr.csv` | MIMIC most-recent (≤24 h) features + outcome | `cs_features_baseline` most-recent projection (`analysis/mr.sql`) |
| `/tmp/feat_baseline.csv` | MIMIC full baseline feature set | `3_UPDATED_CS_MORT_STUDY.cs_features_baseline` |
| `/tmp/mimic_variants.csv` | MIMIC most-recent + anion gap + common variables | `cs_features_canonical` (± `mimic_ag`) |
| `/tmp/mimic_ag.csv` | MIMIC harmonized anion gap | `cs_features_canonical.aniongap_harmonized` |
| `/tmp/eicu.csv` | eICU external features + outcome | `cs_eicu_canonical` |
| `/tmp/eicu_cmp.csv` | eICU comparator-score inputs (BOS,MA2 etc.) | `cs_eicu_comparators` |
| `/tmp/scai.csv` | SCAI-stage components (MIMIC) | `cs_scai_components_mimic` |
| `/tmp/outcomes.csv` | outcomes incl. 30-day mortality | cohort outcome projection |
| `/tmp/horizon_mr.csv` | anytime/horizon most-recent features | `analysis/horizon_mr.sql` |
| `/tmp/csmort7_integer.json` | integer point map (companion CS-MORT-7) | produced by `integer_score.py` |

**Note.** These development scripts are retained for transparency of the model-selection process. They are not required to reproduce the manuscript: the canonical scripts above (and `../../supplementary_analyses/`) do that from `outputs/tables/` with `YOUR_PROJECT_ID` and seed 42.
