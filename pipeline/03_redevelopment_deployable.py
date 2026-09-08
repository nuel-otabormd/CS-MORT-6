"""Redevelopment sensitivity analysis, deployable candidate pool.

Bootstrap-stability selection nested inside 10-times-repeated 5-fold outer
cross-validation, executed under the decision rule archived in PROTOCOL.md
before this script was run. MIMIC-IV landmark only; eICU untouched.
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

POOL = ['age', 'ohca_arrest', 'aniongap_h', 'sodium', 'chloride', 'bicarbonate',
        'bun', 'rdw', 'creatinine', 'hemoglobin', 'sbp_min', 'mech_vent', 'pressor_count']
V2_LAC = ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
V2_AG  = ['aniongap_h', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']

# ---- assemble the LM24 analysis frame (pool + incumbent variables) ----
d = pd.read_csv(DATA + 'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap_h'})
d = d.merge(pd.read_csv(SCRATCH + 'mimic_exact_lm_flags.csv'), on='stay_id')
d = d.merge(pd.read_csv(SCRATCH + 'mimic_extra_candidates.csv'), on='stay_id', how='left')
h24 = pd.read_csv(SCRATCH + 'horizon_mr.csv')
h24 = h24[h24.horizon_h == 24][['stay_id', 'creatinine']]
sc = pd.read_csv(DATA + 'scai_components_mimic.csv')[['stay_id', 'sbp_min', 'pressor_count']]
d = d.merge(h24, on='stay_id', how='left').merge(sc, on='stay_id', how='left')
lm = d[d['exact_lm24'] == 1].reset_index(drop=True)
y = lm['in_hospital_mortality'].astype(int).values
assert len(lm) == 2694

def prep(train, test, cols):
    X = train[cols].astype(float)
    lo, hi = X.quantile(.01), X.quantile(.99)
    Xw = X.clip(lo, hi, axis=1); med = Xw.median()
    mu = Xw.fillna(med).mean(); sd = Xw.fillna(med).std(ddof=0).replace(0, 1)
    def z(df):
        return ((df[cols].astype(float).clip(lo, hi, axis=1).fillna(med)) - mu) / sd
    return z(train), z(test)

# ---- nested challenger + comparators on identical folds ----
n_rep, sel_freq = 10, {c: 0 for c in POOL}
oof_ch = np.zeros((n_rep, len(lm))); oof_l = np.zeros((n_rep, len(lm))); oof_a = np.zeros((n_rep, len(lm)))
n_sel_per_fold = []
for rep in range(n_rep):
    skf = StratifiedKFold(5, shuffle=True, random_state=100 + rep)
    for tr, te in skf.split(lm, y):
        Ztr, Zte = prep(lm.iloc[tr], lm.iloc[te], POOL)
        # selection: 100-bootstrap L1 frequency on the outer-train
        rng = np.random.default_rng(1000 * rep + tr[0])
        freq = np.zeros(len(POOL))
        for _ in range(100):
            i = rng.integers(0, len(tr), len(tr))
            if len(np.unique(y[tr][i])) < 2: continue
            l1 = LogisticRegression(penalty='l1', solver='saga', C=0.5, max_iter=2000)
            l1.fit(Ztr.values[i], y[tr][i])
            freq += (np.abs(l1.coef_[0]) > 1e-8)
        freq /= 100
        order = np.argsort(-freq)
        chosen = [POOL[j] for j in order if freq[j] >= 0.60][:6]
        if not chosen: chosen = [POOL[order[0]]]
        n_sel_per_fold.append(len(chosen))
        for c in chosen: sel_freq[c] += 1
        ridge = LogisticRegression(max_iter=800, C=0.5).fit(Ztr[chosen], y[tr])
        oof_ch[rep, te] = ridge.predict_proba(Zte[chosen])[:, 1]
        # comparators, identical folds
        for cols, store in [(V2_LAC, oof_l), (V2_AG, oof_a)]:
            Ztr2, Zte2 = prep(lm.iloc[tr], lm.iloc[te], cols)
            m = LogisticRegression(max_iter=800, C=0.5).fit(Ztr2, y[tr])
            store[rep, te] = m.predict_proba(Zte2)[:, 1]

p_ch, p_l, p_a = oof_ch.mean(0), oof_l.mean(0), oof_a.mean(0)

def slope_citl(p, yv):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9); lp = np.log(p / (1 - p))
    return (sm.Logit(yv, sm.add_constant(lp)).fit(disp=0).params[1],
            sm.Logit(yv, np.ones(len(yv)), offset=lp).fit(disp=0).params[0])
def net_benefit(p, yv, t):
    return np.mean((p >= t) * yv) - np.mean((p >= t) * (1 - yv)) * (t / (1 - t))

print("=" * 70)
print("CHALLENGER RESULT (per FROZEN_PROTOCOL_20260908.md)")
print("=" * 70)
for p, lab in [(p_ch, 'challenger'), (p_l, 'v2.0 lactate'), (p_a, 'v2.0 anion gap')]:
    sl, ci = slope_citl(p, y)
    print(f"  {lab:16s} AUROC {roc_auc_score(y, p):.4f}  slope {sl:.2f}  CITL {ci:+.3f}  "
          f"Brier {np.mean((p - y) ** 2):.4f}  NB20 {net_benefit(p, y, .2):.4f}  NB40 {net_benefit(p, y, .4):.4f}")

rng = np.random.default_rng(42)
d_l, d_a = [], []
for _ in range(2000):
    i = rng.integers(0, len(y), len(y))
    if len(np.unique(y[i])) > 1:
        d_l.append(roc_auc_score(y[i], p_ch[i]) - roc_auc_score(y[i], p_l[i]))
        d_a.append(roc_auc_score(y[i], p_ch[i]) - roc_auc_score(y[i], p_a[i]))
print(f"\n  paired dAUROC challenger - v2.0 lactate : {np.mean(d_l):+.4f} "
      f"(95% CI {np.percentile(d_l, 2.5):+.4f} to {np.percentile(d_l, 97.5):+.4f})")
print(f"  paired dAUROC challenger - v2.0 anion gap: {np.mean(d_a):+.4f} "
      f"(95% CI {np.percentile(d_a, 2.5):+.4f} to {np.percentile(d_a, 97.5):+.4f})")

print(f"\n  outer-fold selection frequency (50 folds): "
      + ", ".join(f"{c.replace('_h','')} {100*v/50:.0f}%" for c, v in sorted(sel_freq.items(), key=lambda kv: -kv[1])))
print(f"  predictors per fold: median {int(np.median(n_sel_per_fold))} (range {min(n_sel_per_fold)}-{max(n_sel_per_fold)})")

# full-data challenger model (reported regardless of decision)
Zfull, _ = prep(lm, lm, POOL)
rngF = np.random.default_rng(7)
freqF = np.zeros(len(POOL))
for _ in range(100):
    i = rngF.integers(0, len(y), len(y))
    l1 = LogisticRegression(penalty='l1', solver='saga', C=0.5, max_iter=2000).fit(Zfull.values[i], y[i])
    freqF += (np.abs(l1.coef_[0]) > 1e-8)
freqF /= 100
orderF = np.argsort(-freqF)
finalvars = [POOL[j] for j in orderF if freqF[j] >= 0.60][:6]
print(f"\n  full-data challenger variables: {finalvars}")
print(f"  their outer-fold selection frequencies: "
      + ", ".join(f"{c} {100*sel_freq[c]/50:.0f}%" for c in finalvars))

pd.DataFrame({'variable': POOL,
              'outer_fold_selection_pct': [100 * sel_freq[c] / 50 for c in POOL],
              'fulldata_bootstrap_pct': 100 * freqF}).to_csv(OUT + 'challenger_selection.csv', index=False)
res = pd.DataFrame([
    dict(model='challenger', auroc=round(roc_auc_score(y, p_ch), 4)),
    dict(model='v2.0 lactate', auroc=round(roc_auc_score(y, p_l), 4)),
    dict(model='v2.0 anion gap', auroc=round(roc_auc_score(y, p_a), 4)),
    dict(model='paired diff vs lactate', auroc=f"{np.mean(d_l):+.4f} ({np.percentile(d_l,2.5):+.4f},{np.percentile(d_l,97.5):+.4f})"),
    dict(model='paired diff vs anion gap', auroc=f"{np.mean(d_a):+.4f} ({np.percentile(d_a,2.5):+.4f},{np.percentile(d_a,97.5):+.4f})"),
])
res.to_csv(OUT + 'challenger_result.csv', index=False)
print("\n[done] challenger_selection.csv, challenger_result.csv")
