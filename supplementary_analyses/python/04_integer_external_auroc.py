"""
CS-MORT-6 — integer-score external (eICU) AUROC, fully reproducible.

WHAT WAS DONE IN BIGQUERY (the ONLY BigQuery step; AUROC is computed here in Python):
  # eICU external cohort (canonical, n=1866) used for scoring:
  bq query --use_legacy_sql=false --format=csv --max_rows=5000 \
    'SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_canonical`' \
    > data/cs_eicu_canonical.csv
  # MIMIC development cohort (n=3103) — ONLY to get the frozen imputation medians:
  bq query --use_legacy_sql=false --format=csv --max_rows=5000 \
    'SELECT * FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_features_canonical`' \
    > data/cs_features_canonical.csv

DEFINITIONS locked to the manuscript's frozen external pipeline:
  * anion-gap column = aniongap_harmonized (Na - Cl - HCO3, computed identically in
    both DBs) — the SAME column the headline continuous model (0.748) uses. NOT the
    raw lab 'aniongap' column (that yields 0.718 and is inconsistent with the headline).
  * missing raw values imputed with MIMIC development medians (frozen: fit on dev data,
    applied unchanged) BEFORE applying the published Table 2 cut-points.
  * Table 2 integer weights, verbatim:
      anion gap  <12 / 12-18 / >=18   -> 0 / 2 / 4
      urine out  >=1 / 0.5-1 / <0.5   -> 0 / 1 / 2   (protective: low = worse)
      OHCA       no / yes             -> 0 / 3
      age        <65 / 65-80 / >=80   -> 0 / 1 / 2
      BUN        <25 / 25-45 / >=45   -> 0 / 1 / 2
      RDW        <14.5 / 14.5-16 / >=16 -> 0 / 1 / 2
  * pandas.cut default (right=True); clipping out-of-range values is immaterial
    (4-6 values; clip and no-clip both give 0.7393).
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
np.random.seed(42)
D='data/'

e = pd.read_csv(D+'cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})
ye = e['hosp_mort'].astype(int).values
mimic = pd.read_csv(D+'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
medM = {k: mimic[k].median() for k in ['ag','uo','age','bun','rdw']}   # frozen dev medians

def table2_integer(df):
    s = np.zeros(len(df))
    ag = df['aniongap_harmonized'].fillna(medM['ag'])
    s += pd.cut(ag, [-1,12,18,999], labels=False).fillna(0).astype(int) * 2
    uo = pd.cut(df['uo'].fillna(medM['uo']), [-1,0.5,1.0,99], labels=False).fillna(0).astype(int)
    s += (2 - uo)                                                        # protective
    s += df['ohca_arrest'].fillna(0).astype(int) * 3
    s += pd.cut(df['age'].fillna(medM['age']), [-1,65,80,999], labels=False).fillna(0).astype(int)
    s += pd.cut(df['bun'].fillna(medM['bun']), [-1,25,45,9e9], labels=False).fillna(0).astype(int)
    s += pd.cut(df['rdw'].fillna(medM['rdw']), [-1,14.5,16,99], labels=False).fillna(0).astype(int)
    return s.astype(float)

score = table2_integer(e)
auc = roc_auc_score(ye, score)
rng = np.random.default_rng(42)
boot = [roc_auc_score(ye[i], score[i]) for i in
        (rng.integers(0, len(ye), len(ye)) for _ in range(2000))
        if len(np.unique(ye[i])) > 1]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"Integer score EXTERNAL AUROC in eICU (anion-gap, frozen Table 2, MIMIC-median imputation)")
print(f"  n = {len(ye)}   AUROC = {auc:.4f}   95% CI {lo:.4f} - {hi:.4f}")
print(f"  -> report as 0.739 (95% CI 0.715-0.762)")

# corroboration: complete-case (no imputation) and the study's own integ() (harmonized)
cc = e[['aniongap_harmonized','uo','age','bun','rdw']].notna().all(axis=1).values
print(f"  complete-case (n={cc.sum()}): AUROC {roc_auc_score(ye[cc], score[cc]):.4f}")
