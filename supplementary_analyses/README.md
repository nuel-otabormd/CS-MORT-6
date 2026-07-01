# CS-MORT-6 — Supplementary analyses and figures

Self-contained scripts that reproduce the study's supplementary analyses and figures (Figures 2–5 and Supplementary Figures S1–S3). Replace `YOUR_PROJECT_ID` with your Google Cloud project and run from this directory. Seed 42 throughout.

## Contents
- **Pipeline verification** — confirms the integer-scoring pipeline reproduces the published integer points, the SCAI stage distribution (C=1000, D=781, E=850), and the within-stage figure.
- **Within-stage resolution** — score-tertile mortality within each SCAI stage, including two sensitivity variants: the score without out-of-hospital cardiac arrest (Figure S1) and a score built from only the variables not used in stage assignment (Figure S3).
- **Subgroup performance** — discrimination and calibration by sex and race, with event counts (Figure S2 / Table S7).
- **Diagnostics and sensitivity** — anion-gap/BUN collinearity (correlation, VIF, bootstrap reselection), multiple-imputation vs median imputation, and the discrimination difference vs the BOS,MA2 comparator (bootstrap 95% CI).
- **Integer-score external performance** — external (eICU) AUROC of the integer score: 0.739 (95% CI 0.715–0.762).

## Directory
```
supplementary_analyses/
├── sql/exports.sql                 # BigQuery exports -> data/ (YOUR_PROJECT_ID)
├── python/
│   ├── 01_verify_pipeline.py       # reproduces integer points / SCAI dist / within-stage cells
│   ├── 02_sensitivity_subgroup.py  # OHCA-free within-stage, collinearity, subgroup, imputation, AUROC diff -> out/
│   ├── 03_nonstaging_withinstage.py# within-stage using only non-staging variables -> out/
│   └── 04_integer_external_auroc.py# integer-score external AUROC (eICU)
├── r/
│   ├── theme_csmort.R              # shared 300-DPI publication theme
│   └── render_figures.R            # Figures 2–5 and S1–S3
├── data/    (git-ignored; patient-level exports)
├── out/     (script-generated intermediate CSVs)
└── figures/ (rendered TIFF/PNG/PDF)
```

## Reproduce (from this directory)

**1. Populate `data/`** with the exports in `sql/exports.sql` (replace `YOUR_PROJECT_ID`), e.g.:
```bash
bq query --use_legacy_sql=false --format=csv --max_rows=100000 \
  'SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_canonical`' \
  > data/cs_features_canonical.csv
# ...repeat for [2]-[6] in sql/exports.sql
```
Then copy the figure-input CSVs into `data/`: `cal_mimic6.csv`, `cal_eicu6.csv`, `dca_eicu_cm6.csv` (patient-level predictions from `python/analysis/csmort6_final.py`) and `fig4_withinstage.csv`, `fig5_trajectory.csv` (aggregate, from `outputs/tables_aggregate/`).

**2. Run the analyses** (Python 3.9+, `pandas scikit-learn scipy statsmodels`):
```bash
python3 python/01_verify_pipeline.py         # reproduces integer points / SCAI dist / within-stage cells
python3 python/02_sensitivity_subgroup.py    # writes out/*.csv
python3 python/03_nonstaging_withinstage.py  # writes out/fig_s3_nonstaging_withinstage.csv
python3 python/04_integer_external_auroc.py  # prints integer external AUROC = 0.7393
```

**3. Render figures** (R 4.x, `ggplot2 patchwork scales dplyr tidyr`):
```bash
Rscript r/render_figures.R                   # -> figures/*.tiff, *.png, *.pdf (300 DPI)
```

## Notes
- Integer external AUROC uses the harmonized anion gap (`aniongap_harmonized`, Na−Cl−HCO₃) with frozen MIMIC-development-median imputation and the published cut-points, consistent with the main external model.
- Patient-level CSVs in `data/` are PhysioNet-credentialed data and are git-ignored; do not commit them.
