"""CS-MORT-6 landmark development (MIMIC-IV).

Defines the 24-hour landmark population from exact timestamps, fits the frozen
preprocessing and ridge recipe for both formulations, and writes cross-validated
out-of-fold predictions, coefficients, and the full model specification.
"""
import warnings; warnings.filterwarnings('ignore')
import json
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
CONT = ['lactate', 'uo', 'age', 'bun', 'rdw']          # continuous predictors (OHCA is binary)

# ---------------------------------------------------------------- data
d = pd.read_csv(DATA + 'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
fl = pd.read_csv(SCRATCH + 'mimic_exact_lm_flags.csv')
d = d.merge(fl, on='stay_id', validate='1:1')
lm = d[d['exact_lm24'] == 1].reset_index(drop=True)
y  = lm['in_hospital_mortality'].astype(int).values
print(f"[cohort] exact LM24: n={len(lm)}  deaths={y.sum()}  mortality={100*y.mean():.1f}%")
print(f"[cohort] excluded from all-comers 3,103: {3103-len(lm)} "
      f"(died on/before 24h or left ICU before 24h)")

# ------------------------------------------------- continuous v2.0 (ridge, refit at LM24)
def fit_frozen(df, yv, cols):
    """Winsorize 1-99, median-impute, standardize, ridge C=0.5. Returns dict of
    everything needed to reproduce a prediction from raw values."""
    X = df[cols].astype(float)
    lo, hi = X.quantile(.01), X.quantile(.99)
    Xw = X.clip(lo, hi, axis=1)
    med = Xw.median()
    Xi = Xw.fillna(med)
    mu, sd = Xi.mean(), Xi.std(ddof=0)
    Z = (Xi - mu) / sd
    lr = LogisticRegression(max_iter=800, C=0.5).fit(Z, yv)
    return dict(cols=cols, lo=lo, hi=hi, med=med, mu=mu, sd=sd,
                beta=pd.Series(lr.coef_[0], index=cols), b0=float(lr.intercept_[0]))

def predict_frozen(m, df):
    X = df[m['cols']].astype(float).clip(m['lo'], m['hi'], axis=1).fillna(m['med'])
    Z = (X - m['mu']) / m['sd']
    lp = m['b0'] + Z.values @ m['beta'].values
    return 1 / (1 + np.exp(-lp))

def slope_citl(p, yv):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    lp = np.log(p / (1 - p))
    sl = sm.Logit(yv, sm.add_constant(lp)).fit(disp=0).params[1]
    ci = sm.Logit(yv, np.ones(len(yv)), offset=lp).fit(disp=0).params[0]
    return sl, ci

def auc_ci(yv, p, B=2000, seed=42):
    rng = np.random.default_rng(seed); a = []
    for _ in range(B):
        i = rng.integers(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1:
            a.append(roc_auc_score(yv[i], np.asarray(p)[i]))
    return np.percentile(a, [2.5, 97.5])

COLS = ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
# out-of-fold internal validation: every preprocessing step fit inside the fold
oof = np.zeros(len(lm))
fold_id = np.zeros(len(lm), int)
for k, (tr, te) in enumerate(StratifiedKFold(5, shuffle=True, random_state=42).split(lm, y)):
    mk = fit_frozen(lm.iloc[tr], y[tr], COLS)
    oof[te] = predict_frozen(mk, lm.iloc[te])
    fold_id[te] = k
a = roc_auc_score(y, oof); lo_, hi_ = auc_ci(y, oof); sl, ci = slope_citl(oof, y)
print(f"\n[v2.0 continuous, lactate form] 5-fold CV (all preprocessing in-fold)")
print(f"  AUROC {a:.4f} ({lo_:.4f}-{hi_:.4f})   slope {sl:.2f}   CITL {ci:+.3f}")

# context: submitted v1.1 recipe (trained on all-comers) evaluated on the same LM24 patients
v11 = fit_frozen(d, d['in_hospital_mortality'].astype(int).values, COLS)
p11 = predict_frozen(v11, lm)
print(f"  [context] v1.1 all-comers model on exact LM24: AUROC {roc_auc_score(y, p11):.4f}")

# anion-gap formulation, same recipe
COLS_AG = ['aniongap', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
oof_ag = np.zeros(len(lm))
for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(lm, y):
    mk = fit_frozen(lm.iloc[tr], y[tr], COLS_AG)
    oof_ag[te] = predict_frozen(mk, lm.iloc[te])
a2 = roc_auc_score(y, oof_ag); lo2, hi2 = auc_ci(y, oof_ag); sl2, ci2 = slope_citl(oof_ag, y)
print(f"[v2.0 continuous, anion-gap form] AUROC {a2:.4f} ({lo2:.4f}-{hi2:.4f})   "
      f"slope {sl2:.2f}   CITL {ci2:+.3f}")

# frozen final models on full LM24 (the deployable v2.0 specification)
m_lac = fit_frozen(lm, y, COLS)
m_ag  = fit_frozen(lm, y, COLS_AG)
spec_rows = []
for name, m in [('lactate', m_lac), ('anion-gap', m_ag)]:
    beta_raw = m['beta'] / m['sd']
    b0_raw = m['b0'] - float((m['beta'] * m['mu'] / m['sd']).sum())
    for c in m['cols']:
        spec_rows.append(dict(model=name, variable=c,
            winsor_lo=round(float(m['lo'][c]), 4), winsor_hi=round(float(m['hi'][c]), 4),
            impute_median=round(float(m['med'][c]), 4),
            mean=round(float(m['mu'][c]), 4), sd=round(float(m['sd'][c]), 4),
            beta_standardized=round(float(m['beta'][c]), 6),
            beta_raw_scale=round(float(beta_raw[c]), 6)))
    spec_rows.append(dict(model=name, variable='(intercept)',
        beta_standardized=round(m['b0'], 6), beta_raw_scale=round(b0_raw, 6)))
pd.DataFrame(spec_rows).to_csv(OUT + 'v2_spec_continuous.csv', index=False)
print(f"\n[spec] exact intercepts: lactate {m_lac['b0']:+.4f} (standardized scale), "
      f"anion-gap {m_ag['b0']:+.4f}; full spec -> v2_spec_continuous.csv")

# ------------------------------------------------- integer card v2.0 (card = code)
BINS_RISK = {'lactate': [-1, 2, 4, 999], 'bun': [-1, 25, 45, 9e9],
             'age': [-1, 65, 80, 999], 'rdw': [-1, 14.5, 16, 999]}
BINS_PROT = {'uo': [-1, 0.5, 1.0, 999]}

def ordinal_frame(df, med_ref):
    """Left-inclusive bins so written thresholds match the code. Missing values take
    the category of the reference median value (printed in the card)."""
    cols = {}
    for f in F6:
        if f == 'ohca_arrest':
            cols[f] = df[f].fillna(0).astype(int).values
        elif f in BINS_PROT:
            v = df[f].fillna(med_ref[f])
            o = pd.cut(v, bins=BINS_PROT[f], labels=False, right=False)
            cols[f] = (2 - o.fillna(0)).astype(int).values      # protective: high uo = 0 pts
        else:
            v = df[f].fillna(med_ref[f])
            cols[f] = pd.cut(v, bins=BINS_RISK[f], labels=False, right=False)\
                        .fillna(0).astype(int).values
    return np.column_stack([cols[f] for f in F6])

def derive_points(O, yv, seed=None):
    lr = LogisticRegression(max_iter=800)
    if seed is not None:
        np.random.seed(seed)
    lr.fit(O, yv)
    b = np.abs(lr.coef_[0]); B = np.median(b)
    return np.maximum(1, np.round(b / B)).astype(int)

med_lm = lm[CONT].median()
O = ordinal_frame(lm, med_lm)
pts = derive_points(O, y)
score = (O * pts).sum(1)
print(f"\n[integer v2.0] per-level points: {dict(zip(F6, pts))}  score range {score.min()}-{score.max()}")
print(f"  (v1.1 card for comparison: lactate 2/level, uo 1, ohca 3, age 1, bun 1, rdw 1; range 0-15)")
imp_cat = {f: int(pd.cut(pd.Series([med_lm[f]]), bins=(BINS_PROT.get(f) or BINS_RISK[f]),
           labels=False, right=False)[0]) for f in CONT}
print(f"  missing-value default categories (from LM24 medians {dict(round(med_lm,2))}): {imp_cat}")

a_in = roc_auc_score(y, score)
# optimism: rederive points inside each bootstrap
optim = []
rng = np.random.default_rng(42)
for _ in range(500):
    i = rng.integers(0, len(y), len(y))
    pb = derive_points(O[i], y[i])
    optim.append(roc_auc_score(y[i], (O[i] * pb).sum(1)) - roc_auc_score(y, (O * pb).sum(1)))
# fold-honest CV: points rederived per training fold
oof_int = np.zeros(len(lm))
for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(lm, y):
    med_tr = lm.iloc[tr][CONT].median()
    Otr = ordinal_frame(lm.iloc[tr], med_tr); Ote = ordinal_frame(lm.iloc[te], med_tr)
    ptr = derive_points(Otr, y[tr])
    oof_int[te] = (Ote * ptr).sum(1)
a_cv = roc_auc_score(y, oof_int); loi, hii = auc_ci(y, oof_int)
print(f"  in-sample AUROC {a_in:.4f} | optimism-corrected {a_in-np.mean(optim):.4f} "
      f"| fold-honest CV {a_cv:.4f} ({loi:.4f}-{hii:.4f})")

# risk bands from predicted-risk cuts <10/20/40/60% (same derivation rule as v1.1)
band_lr = LogisticRegression(max_iter=500).fit(score.reshape(-1, 1), y)
uniq = np.arange(score.min(), score.max() + 1)
risk_by_score = band_lr.predict_proba(uniq.reshape(-1, 1))[:, 1]
edges = [uniq[risk_by_score < t].max() if (risk_by_score < t).any() else uniq[0] - 1
         for t in [.10, .20, .40, .60]]
print(f"  score->predicted risk: " +
      " ".join(f"{s}:{100*r:.0f}%" for s, r in zip(uniq, risk_by_score)))
print(f"  band upper edges (<10/20/40/60% predicted): {edges}")
rows = []
labels = ['Low', 'Moderate', 'High', 'Very high']
cuts = [score.min() - 1] + edges[1:] + [score.max()]
# assemble bands from the <20/40/60 edges with a Low band below the 20% edge
b_edges = [score.min() - 1, edges[1], edges[2], edges[3], score.max()]
for i, lab in enumerate(labels):
    mk = (score > b_edges[i]) & (score <= b_edges[i + 1])
    rows.append(dict(band=lab, scores=f"{int(b_edges[i]+1)}-{int(b_edges[i+1])}",
                     n=int(mk.sum()), mortality=round(100 * y[mk].mean(), 1)))
bands = pd.DataFrame(rows)
print(bands.to_string(index=False))

card = pd.DataFrame({'variable': F6, 'points_per_level': pts,
                     'levels': ['<2 / 2-4 / >=4', '>=1 / 0.5-1 / <0.5', 'no / yes',
                                '<65 / 65-80 / >=80', '<25 / 25-45 / >=45', '<14.5 / 14.5-16 / >=16']})
card.to_csv(OUT + 'v2_integer_card.csv', index=False)
bands.to_csv(OUT + 'v2_risk_bands.csv', index=False)

perf = pd.DataFrame([
    dict(item='LM24 n / deaths / mortality', value=f"{len(lm)} / {y.sum()} / {100*y.mean():.1f}%"),
    dict(item='v2.0 continuous lactate CV AUROC', value=f"{a:.4f} ({lo_:.4f}-{hi_:.4f})"),
    dict(item='v2.0 continuous lactate CV slope/CITL', value=f"{sl:.2f} / {ci:+.3f}"),
    dict(item='v2.0 continuous anion-gap CV AUROC', value=f"{a2:.4f} ({lo2:.4f}-{hi2:.4f})"),
    dict(item='v1.1 all-comers model on LM24 (context)', value=f"{roc_auc_score(y, p11):.4f}"),
    dict(item='v2.0 integer in-sample / optimism / CV', value=f"{a_in:.4f} / {a_in-np.mean(optim):.4f} / {a_cv:.4f}"),
])
perf.to_csv(OUT + 'v2_internal_performance.csv', index=False)
pd.DataFrame({'stay_id': lm['stay_id'], 'fold': fold_id, 'oof_lac': oof,
              'oof_ag': oof_ag, 'oof_int': oof_int, 'score_v2': score, 'y': y})\
  .to_csv(SCRATCH + 'v2_oof_predictions.csv', index=False)
print("\n[done] aggregate outputs written; patient-level OOF predictions in the data directory")
