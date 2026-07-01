# CS-MORT-6

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20617607.svg)](https://doi.org/10.5281/zenodo.20617607)

Code and reproduction materials for **"CS-MORT-6: Refining Cardiogenic Shock Risk Within SCAI
Stages Through a Serially Computable Bedside Mortality Score."**

A six-variable bedside in-hospital mortality score for cardiogenic shock (lactate, urine output,
out-of-hospital cardiac arrest, age, blood urea nitrogen, red cell distribution width; anion-gap
substitution for lactate), developed in MIMIC-IV and externally validated in the eICU Collaborative
Research Database. Reporting follows TRIPOD+AI.

## Repository structure
- `sql/` — cohort and feature-extraction queries (BigQuery / PhysioNet `physionet-data`).
  - `01_cohort_generation.sql`, `06_features_canonical_mr.sql` (MIMIC features),
    `07_eicu_canonical.sql` (eICU, harmonized anion gap), `08_mimic_demographics.sql`,
    `09_scai_components.sql`, `10_eicu_scai_components.sql`, plus `03/03b/04/05`.
- `python/` — analysis and figure/manuscript-generation scripts.
  - `analysis/csmort6_results.py` (canonical results: discrimination, calibration, risk categories,
    comparators), `csmort6_final.py`, `fairness_heterogeneity.py`, `scai_rebuild.py`,
    `eicu_withinstage.py`, `dynamic_trajectory.py`, `missingness_analysis.py`, `reaudit.py`.
  - `analysis/figs6.R`, `headline_figures.R`, `figure1_consort.R` (figures).
  - `CS_MORT_6_Analysis.ipynb` (executes the pipeline end to end).
- `outputs/tables_aggregate/` — **aggregate** result tables only (no patient-level rows).
- `figures/` — the five main figures (PNG).
- `supplementary_analyses/` — self-contained scripts (SQL + Python + R) that reproduce the
  supplementary analyses and figures: pipeline verification, within-stage resolution (including
  OHCA-free and non-staging-variable variants), subgroup performance, imputation and comparator
  sensitivity, and integer-score external performance. See its `README.md`.

## Data availability (important)
The analytic datasets are derived from **MIMIC-IV (v3.1)** and the **eICU Collaborative Research
Database**, both available from **PhysioNet (https://physionet.org)** to credentialed researchers
who complete the required training and data use agreements. The PhysioNet DUA prohibits
redistribution of the data, so **patient-level derived files are NOT included here** (see
`.gitignore`). Credentialed users can regenerate every analytic table by running the SQL in `sql/`
and then the scripts in `python/analysis/`. Only aggregate result tables are committed.

## Reproduction
1. Obtain MIMIC-IV v3.1 and eICU via PhysioNet; load into BigQuery (`physionet-data`).
2. Run `sql/01`, `06`, `07`, `08`, `09`, `10` (and `03/04/05`) to build the analytic tables.
3. Export the analytic tables to `outputs/tables/` (queries are deterministic; see file headers).
4. Run `python/analysis/csmort6_results.py`, `fairness_heterogeneity.py`, `scai_rebuild.py`,
   `eicu_withinstage.py`, `dynamic_trajectory.py`; then `figs6.R` and `headline_figures.R`.
5. `reaudit.py` reproduces the headline numbers from the committed aggregate tables.
Environment: Python 3.9 (scikit-learn 1.6.1, pandas, numpy, scipy), R (ggplot2); fixed seed 42.


## Configuration
The SQL and scripts reference a placeholder Google Cloud project, `YOUR_PROJECT_ID`. Replace it with your own project ID (and adjust the BigQuery dataset name if desired) before running.

## License
Code is released under the MIT License (`LICENSE`). The manuscript and figures are © the authors.
