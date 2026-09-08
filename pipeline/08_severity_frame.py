"""Severity-frame (all-admissions) performance.

Day-1 estimates for both cohorts under corrected card thresholds, with
decision-curve values; retained for comparability with existing scores.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
DATA    = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'
SCRATCH = DATA
OUT     = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
np.random.seed(42)

F6 = ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
CONT = ['lactate', 'uo', 'age', 'bun', 'rdw']
CARD = {'lactate': 2, 'uo': 1, 'ohca_arrest': 3, 'age': 1, 'bun': 1, 'rdw': 1}
BINS_RISK = {'lactate': [-1, 2, 4, 999], 'bun': [-1, 25, 45, 9e9],
             'age': [-1, 65, 80, 999], 'rdw': [-1, 14.5, 16, 999]}
BINS_PROT = {'uo': [-1, 0.5, 1.0, 999]}

d = pd.read_csv(DATA + 'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
y = d['in_hospital_mortality'].astype(int).values
MED_ALL = d[CONT + ['aniongap']].median()

def card_score(df, med, ag_for_lactate=False):
    total = np.zeros(len(df))
    for f in F6:
        if f == 'ohca_arrest':
            total += df[f].fillna(0).astype(int).values * CARD[f]
        elif f in BINS_PROT:
            o = pd.cut(df[f].fillna(med[f]), bins=BINS_PROT[f], labels=False, right=False)
            total += (2 - o.fillna(0)).astype(int).values * CARD[f]
        elif f == 'lactate' and ag_for_lactate:
            o = pd.cut(df['aniongap'].fillna(med['aniongap']),
                       bins=[-1, 12, 18, 999], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD['lactate']
        else:
            o = pd.cut(df[f].fillna(med[f]), bins=BINS_RISK[f], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD[f]
    return total.astype(int)

def auc_ci(yv, p, B=2000):
    rng = np.random.default_rng(42); a = []
    for _ in range(B):
        i = rng.integers(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1: a.append(roc_auc_score(yv[i], np.asarray(p)[i]))
    return np.percentile(a, [2.5, 97.5])

print("SEVERITY FRAME, regenerated under corrected binning (all-comers, n=%d)" % len(d))
# internal integer, fold-honest (training-fold medians for missing defaults)
oof = np.zeros(len(d), int)
for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(d, y):
    med_tr = d.iloc[tr][CONT + ['aniongap']].median()
    oof[te] = card_score(d.iloc[te], med_tr)
a = roc_auc_score(y, oof); lo, hi = auc_ci(y, oof)
print(f"  internal integer (corrected binning, OOF): {a:.4f} ({lo:.4f}-{hi:.4f})   [submitted, old binning: 0.765]")

# external integer, frozen all-comers card (anion-gap substitution), corrected binning
e = pd.read_csv(DATA + 'cs_eicu_canonical.csv').drop(columns=['aniongap']).rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
ye = e['hosp_mort'].astype(int).values
s_ext = card_score(e, MED_ALL, ag_for_lactate=True)
a2 = roc_auc_score(ye, s_ext); lo2, hi2 = auc_ci(ye, s_ext)
print(f"  external integer AG (corrected binning): {a2:.4f} ({lo2:.4f}-{hi2:.4f})   [submitted, old binning: 0.739]")

# frozen-vs-frozen DCA values from the saved addendum output
dca = pd.read_csv(OUT + 'dca_lm24_common.csv')
for t_ in [0.20, 0.40]:
    r = dca.iloc[(dca['threshold'] - t_).abs().argmin()]
    print(f"  DCA landmark, frozen-vs-frozen at {int(t_*100)}%: CS-MORT-6 {r['cs_mort6_ag']:.3f} | "
          f"BOS,MA2 published {r['bosma2_published']:.3f} | (recalibrated, in-sample: {r['bosma2_recal']:.3f})")

pd.DataFrame([
    dict(item='severity internal integer corrected OOF', value=f"{a:.4f} ({lo:.4f}-{hi:.4f})"),
    dict(item='severity external integer AG corrected', value=f"{a2:.4f} ({lo2:.4f}-{hi2:.4f})"),
]).to_csv(OUT + 'severity_frame_final.csv', index=False)
print("[done] severity_frame_final.csv")
