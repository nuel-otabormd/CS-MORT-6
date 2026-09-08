"""Integer card at the landmark.

Score-to-risk mapping, risk bands with Wilson intervals, out-of-fold integer
performance, and calibration summaries for the 0-to-15 card.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
DATA    = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'
SCRATCH = DATA
OUT     = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
np.random.seed(42)

F6   = ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
CONT = ['lactate', 'uo', 'age', 'bun', 'rdw']
CARD = {'lactate': 2, 'uo': 1, 'ohca_arrest': 3, 'age': 1, 'bun': 1, 'rdw': 1}
BINS_RISK = {'lactate': [-1, 2, 4, 999], 'bun': [-1, 25, 45, 9e9],
             'age': [-1, 65, 80, 999], 'rdw': [-1, 14.5, 16, 999]}
BINS_PROT = {'uo': [-1, 0.5, 1.0, 999]}

d = pd.read_csv(DATA + 'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
fl = pd.read_csv(SCRATCH + 'mimic_exact_lm_flags.csv')
d = d.merge(fl, on='stay_id', validate='1:1')
lm = d[d['exact_lm24'] == 1].reset_index(drop=True)
y = lm['in_hospital_mortality'].astype(int).values

def card_score(df, med_ref):
    total = np.zeros(len(df))
    for f in F6:
        if f == 'ohca_arrest':
            total += df[f].fillna(0).astype(int).values * CARD[f]
        elif f in BINS_PROT:
            o = pd.cut(df[f].fillna(med_ref[f]), bins=BINS_PROT[f], labels=False, right=False)
            total += (2 - o.fillna(0)).astype(int).values * CARD[f]
        else:
            o = pd.cut(df[f].fillna(med_ref[f]), bins=BINS_RISK[f], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD[f]
    return total.astype(int)

def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z**2 / n
    ctr = (p + z**2 / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return 100 * (ctr - hw), 100 * (ctr + hw)

# ---- fold-honest integer scores (training-fold medians for missing defaults) ----
oof_score = np.zeros(len(lm), int)
for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(lm, y):
    med_tr = lm.iloc[tr][CONT].median()
    oof_score[te] = card_score(lm.iloc[te], med_tr)
a = roc_auc_score(y, oof_score)
rng = np.random.default_rng(42)
boots = [roc_auc_score(y[i], oof_score[i]) for i in
         (rng.integers(0, len(y), len(y)) for _ in range(2000)) if len(np.unique(y[i])) > 1]
print(f"[integer, transported card] fold-honest OOF AUROC {a:.4f} "
      f"({np.percentile(boots, 2.5):.4f}-{np.percentile(boots, 97.5):.4f})")

# ---- risk bands with Wilson CIs (OOF scores) ----
rows = []
for lo, hi, lab in [(-1, 3, 'Low 0-3'), (3, 5, 'Moderate 4-5'),
                    (5, 7, 'High 6-7'), (7, 15, 'Very high 8-15')]:
    mk = (oof_score > lo) & (oof_score <= hi)
    k, n = int(y[mk].sum()), int(mk.sum())
    w_lo, w_hi = wilson(k, n)
    rows.append(dict(band=lab, n=n, deaths=k, mortality=round(100 * k / n, 1),
                     ci=f"{w_lo:.1f}-{w_hi:.1f}"))
bands = pd.DataFrame(rows)
print(bands.to_string(index=False))
bands.to_csv(OUT + 'v2_risk_bands_oof.csv', index=False)

# ---- frozen deployment score-to-risk mapping (full LM24; labeled apparent) ----
med_full = lm[CONT].median()
s_full = card_score(lm, med_full)
mapper = LogisticRegression(max_iter=500).fit(s_full.reshape(-1, 1), y)
uniq = np.arange(0, 16)
risk = mapper.predict_proba(uniq.reshape(-1, 1))[:, 1]
obs = [f"{100*y[s_full==s].mean():.1f}% (n={int((s_full==s).sum())})"
       if (s_full == s).sum() >= 10 else 'n<10' for s in uniq]
mapping = pd.DataFrame({'score': uniq, 'predicted_risk_pct': np.round(100 * risk, 1),
                        'observed_lm24': obs})
mapping.to_csv(OUT + 'v2_score_risk_mapping.csv', index=False)
print("\n[mapping] score -> LM24 predicted risk (apparent, deployment mapping):")
print("  " + " ".join(f"{s}:{100*r:.0f}%" for s, r in zip(uniq, risk)))

# ---- continuous OOF calibration: slope/CITL with CIs + decile curve ----
oofp = pd.read_csv(SCRATCH + 'v2_oof_predictions.csv')
assert (oofp['y'].values == y).all()
def slope_citl(p, yv):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    lp = np.log(p / (1 - p))
    sl = sm.Logit(yv, sm.add_constant(lp)).fit(disp=0).params[1]
    ci = sm.Logit(yv, np.ones(len(yv)), offset=lp).fit(disp=0).params[0]
    return sl, ci
for col, lab in [('oof_lac', 'lactate'), ('oof_ag', 'anion gap')]:
    p = oofp[col].values
    sl, ci = slope_citl(p, y)
    sls, cis = [], []
    rng = np.random.default_rng(42)
    for _ in range(1000):
        i = rng.integers(0, len(y), len(y))
        if len(np.unique(y[i])) > 1:
            s_, c_ = slope_citl(p[i], y[i]); sls.append(s_); cis.append(c_)
    print(f"[continuous {lab}] slope {sl:.2f} ({np.percentile(sls,2.5):.2f}-{np.percentile(sls,97.5):.2f})  "
          f"CITL {ci:+.3f} ({np.percentile(cis,2.5):+.3f}-{np.percentile(cis,97.5):+.3f})")
    dec = pd.qcut(p, 10, labels=False, duplicates='drop')
    curve = pd.DataFrame({'decile': range(dec.max() + 1)})
    curve['pred'] = [p[dec == k].mean() for k in curve['decile']]
    curve['obs'] = [y[dec == k].mean() for k in curve['decile']]
    curve['n'] = [int((dec == k).sum()) for k in curve['decile']]
    curve.to_csv(OUT + f'v2_calibration_curve_{col}.csv', index=False)
print("\n[done] stage 1b artifacts in outputs/")
