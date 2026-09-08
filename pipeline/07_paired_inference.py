"""Additional paired inference.

Symmetric-pool redevelopment sensitivity, severity-frame cross-validated
intervals, and paired 48-hour AUROC differences in both cohorts.
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

POOL15 = ['age', 'ohca_arrest', 'aniongap_h', 'sodium', 'chloride', 'bicarbonate',
          'bun', 'rdw', 'creatinine', 'hemoglobin', 'sbp_min', 'mech_vent',
          'pressor_count', 'lactate', 'uo']
V2_LAC_COLS = ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']

d = pd.read_csv(DATA + 'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap_h'})
d = d.merge(pd.read_csv(SCRATCH + 'mimic_exact_lm_flags.csv'), on='stay_id')
d = d.merge(pd.read_csv(SCRATCH + 'mimic_extra_candidates.csv'), on='stay_id', how='left')
h = pd.read_csv(SCRATCH + 'horizon_mr.csv')
d = d.merge(h[h.horizon_h == 24][['stay_id', 'creatinine']], on='stay_id', how='left')
d = d.merge(pd.read_csv(DATA + 'scai_components_mimic.csv')[['stay_id', 'sbp_min', 'pressor_count']],
            on='stay_id', how='left')
lm = d[d['exact_lm24'] == 1].reset_index(drop=True)
y = lm['in_hospital_mortality'].astype(int).values
yA = d['in_hospital_mortality'].astype(int).values

def prep(train, test, cols):
    X = train[cols].astype(float)
    lo, hi = X.quantile(.01), X.quantile(.99)
    Xw = X.clip(lo, hi, axis=1); med = Xw.median()
    mu = Xw.fillna(med).mean(); sd = Xw.fillna(med).std(ddof=0).replace(0, 1)
    def z(df): return ((df[cols].astype(float).clip(lo, hi, axis=1).fillna(med)) - mu) / sd
    return z(train), z(test)

# ---------------- 1. symmetric challenger ----------------
print("=" * 70); print("1. SYMMETRIC CHALLENGER (15 candidates incl. lactate, uo)")
print("=" * 70)
n_rep = 10
oof_ch = np.zeros((n_rep, len(lm))); oof_l = np.zeros((n_rep, len(lm)))
sel = {c: 0 for c in POOL15}
for rep in range(n_rep):
    skf = StratifiedKFold(5, shuffle=True, random_state=100 + rep)
    for tr, te in skf.split(lm, y):
        Ztr, Zte = prep(lm.iloc[tr], lm.iloc[te], POOL15)
        rng = np.random.default_rng(1000 * rep + tr[0])
        freq = np.zeros(len(POOL15))
        for _ in range(100):
            i = rng.integers(0, len(tr), len(tr))
            if len(np.unique(y[tr][i])) < 2: continue
            l1 = LogisticRegression(penalty='l1', solver='saga', C=0.5, max_iter=2000)
            l1.fit(Ztr.values[i], y[tr][i])
            freq += (np.abs(l1.coef_[0]) > 1e-8)
        freq /= 100
        order = np.argsort(-freq)
        chosen = [POOL15[j] for j in order if freq[j] >= 0.60][:6]
        if not chosen: chosen = [POOL15[order[0]]]
        for c in chosen: sel[c] += 1
        ridge = LogisticRegression(max_iter=800, C=0.5).fit(Ztr[chosen], y[tr])
        oof_ch[rep, te] = ridge.predict_proba(Zte[chosen])[:, 1]
        Ztr2, Zte2 = prep(lm.iloc[tr], lm.iloc[te], V2_LAC_COLS)
        m = LogisticRegression(max_iter=800, C=0.5).fit(Ztr2, y[tr])
        oof_l[rep, te] = m.predict_proba(Zte2)[:, 1]
p_ch, p_l = oof_ch.mean(0), oof_l.mean(0)
rng = np.random.default_rng(42); diffs = []
for _ in range(2000):
    i = rng.integers(0, len(y), len(y))
    if len(np.unique(y[i])) > 1:
        diffs.append(roc_auc_score(y[i], p_ch[i]) - roc_auc_score(y[i], p_l[i]))
print(f"  symmetric challenger {roc_auc_score(y, p_ch):.4f} vs v2.0 lactate {roc_auc_score(y, p_l):.4f}")
print(f"  paired diff {np.mean(diffs):+.4f} (95% CI {np.percentile(diffs, 2.5):+.4f} to {np.percentile(diffs, 97.5):+.4f})")
print("  selection frequency (50 outer folds): "
      + ", ".join(f"{c.replace('_h','')} {100*v/50:.0f}%"
                  for c, v in sorted(sel.items(), key=lambda kv: -kv[1]) if v > 0))
pd.DataFrame({'variable': POOL15, 'outer_fold_selection_pct': [100 * sel[c] / 50 for c in POOL15]})\
  .to_csv(OUT + 'challenger_symmetric_selection.csv', index=False)

# ---------------- 2. internal all-comers anion-gap CV CI ----------------
print("=" * 70); print("2. ALL-COMERS ANION-GAP INTERNAL CV AUROC WITH CI")
print("=" * 70)
COLS_AG = ['aniongap_h', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
pA = np.zeros(len(d))
for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(d, yA):
    Ztr, Zte = prep(d.iloc[tr], d.iloc[te], COLS_AG)
    m = LogisticRegression(max_iter=800, C=0.5).fit(Ztr, yA[tr])
    pA[te] = m.predict_proba(Zte)[:, 1]
rngA = np.random.default_rng(42); aa = []
for _ in range(2000):
    i = rngA.integers(0, len(yA), len(yA))
    if len(np.unique(yA[i])) > 1: aa.append(roc_auc_score(yA[i], pA[i]))
print(f"  all-comers AG CV AUROC {roc_auc_score(yA, pA):.4f} ({np.percentile(aa,2.5):.4f}-{np.percentile(aa,97.5):.4f})")

# ---------------- 3+4. 48-h paired CIs + labeled internal recalibration ----------------
print("=" * 70); print("3. MIMIC 48-H: paired CIs + labeled time-specific recalibration")
print("=" * 70)
def fit_frozen(df, yv, cols):
    X = df[cols].astype(float)
    lo, hi = X.quantile(.01), X.quantile(.99)
    Xw = X.clip(lo, hi, axis=1); med = Xw.median()
    Xi = Xw.fillna(med); mu, sd = Xi.mean(), Xi.std(ddof=0)
    lr = LogisticRegression(max_iter=800, C=0.5).fit((Xi - mu) / sd, yv)
    return dict(cols=cols, lo=lo, hi=hi, med=med, mu=mu, sd=sd,
                beta=pd.Series(lr.coef_[0], index=cols), b0=float(lr.intercept_[0]))
def predict(m, df):
    X = df[m['cols']].astype(float).clip(m['lo'], m['hi'], axis=1).fillna(m['med'])
    lp = m['b0'] + (((X - m['mu']) / m['sd']).values @ m['beta'].values)
    return 1 / (1 + np.exp(-lp))
def paired_ci(yv, p1, p2, B=2000):
    rng = np.random.default_rng(42); dd = []
    for _ in range(B):
        i = rng.integers(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1:
            dd.append(roc_auc_score(yv[i], np.asarray(p1)[i]) - roc_auc_score(yv[i], np.asarray(p2)[i]))
    return np.mean(dd), np.percentile(dd, 2.5), np.percentile(dd, 97.5)

lm_ref = d[d['exact_lm24'] == 1]
V2_LAC = fit_frozen(lm_ref.rename(columns={'aniongap_h': 'aniongap'}), lm_ref['in_hospital_mortality'].astype(int).values,
                    ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
V2_AG = fit_frozen(lm_ref.rename(columns={'aniongap_h': 'aniongap'}), lm_ref['in_hospital_mortality'].astype(int).values,
                   ['aniongap', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
h48 = h[h.horizon_h == 48][['stay_id', 'lactate', 'uo_rate', 'bun', 'rdw']].rename(columns={'uo_rate': 'uo'})
lm48 = d[d['exact_lm48'] == 1][['stay_id', 'in_hospital_mortality', 'ohca_arrest', 'age', 'lactate', 'uo', 'bun', 'rdw']]
mrg = lm48.merge(h48, on='stay_id', suffixes=('_24', ''))
y48 = mrg['in_hospital_mortality'].astype(int).values
stale = mrg.rename(columns={'lactate': 'l48', 'uo': 'u48', 'bun': 'b48', 'rdw': 'r48'})\
           .rename(columns={'lactate_24': 'lactate', 'uo_24': 'uo', 'bun_24': 'bun', 'rdw_24': 'rdw'})
p_up, p_st = predict(V2_LAC, mrg), predict(V2_LAC, stale)
mdiff, lo_, hi_ = paired_ci(y48, p_up, p_st)
print(f"  MIMIC updated-vs-stale paired dAUROC {mdiff:+.4f} ({lo_:+.4f} to {hi_:+.4f})")
lp = np.log(np.clip(p_up, 1e-9, 1 - 1e-9) / (1 - np.clip(p_up, 1e-9, 1 - 1e-9)))
delta48 = sm.Logit(y48, np.ones(len(y48)), offset=lp).fit(disp=0).params[0]
p_rec = 1 / (1 + np.exp(-(lp + delta48)))
sl = sm.Logit(y48, sm.add_constant(np.log(p_rec / (1 - p_rec)))).fit(disp=0).params[1]
print(f"  labeled 48-h recalibration intercept (internal): {delta48:+.3f}; post-update slope {sl:.2f}, CITL 0.000 by construction")

print("=" * 70); print("4. eICU 48-H updated-vs-stale paired CI (reporting completion of locked run)")
print("=" * 70)
e48 = pd.read_csv(SCRATCH + 'eicu_48h_clean.csv')
e24 = pd.read_csv(DATA + 'cs_eicu_canonical.csv').drop(columns=['aniongap']).rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
e48 = e48.merge(e24[['patientunitstayid', 'lactate', 'uo', 'bun', 'rdw', 'aniongap']],
                on='patientunitstayid', suffixes=('', '_24h'))
l48 = e48[e48['in_icu_48h'] == 1].copy()
ye48 = l48['hosp_mort'].astype(int).values
upd = l48.rename(columns={'lactate': 'lact24', 'uo': 'uo24', 'bun': 'bun24', 'rdw': 'rdw24', 'aniongap': 'ag24'})\
         .rename(columns={'lactate48': 'lactate', 'uo48': 'uo', 'bun48': 'bun', 'rdw48': 'rdw', 'ag48': 'aniongap'})
pe_up, pe_st = predict(V2_AG, upd), predict(V2_AG, l48)
mdiff, lo_, hi_ = paired_ci(ye48, pe_up, pe_st)
print(f"  eICU AG updated {roc_auc_score(ye48, pe_up):.4f} vs stale {roc_auc_score(ye48, pe_st):.4f}: "
      f"paired dAUROC {mdiff:+.4f} ({lo_:+.4f} to {hi_:+.4f})")
print("\n[STAGE 07 COMPLETE]")
