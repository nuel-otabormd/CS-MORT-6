"""External descriptive analyses (eICU).

Within-stage Figure 1 cells and decision-curve data.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import statsmodels.api as sm

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
DATA    = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'
SCRATCH = DATA
OUT     = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
np.random.seed(42)

F6 = ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
CARD = {'lactate': 2, 'uo': 1, 'ohca_arrest': 3, 'age': 1, 'bun': 1, 'rdw': 1}
BINS_RISK = {'lactate': [-1, 2, 4, 999], 'bun': [-1, 25, 45, 9e9],
             'age': [-1, 65, 80, 999], 'rdw': [-1, 14.5, 16, 999]}
BINS_PROT = {'uo': [-1, 0.5, 1.0, 999]}

# frozen references from MIMIC exact LM24
dm = pd.read_csv(DATA + 'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
dm = dm.merge(pd.read_csv(SCRATCH + 'mimic_exact_lm_flags.csv'), on='stay_id')
lmM = dm[dm['exact_lm24'] == 1]
yM = lmM['in_hospital_mortality'].astype(int).values
MED = lmM[['lactate', 'uo', 'age', 'bun', 'rdw', 'aniongap']].median()

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
V2_AG = fit_frozen(lmM, yM, ['aniongap', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])

def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return 100 * (c - hw), 100 * (c + hw)

def card_score_ag(df):
    total = np.zeros(len(df))
    for f in F6:
        if f == 'ohca_arrest':
            total += df[f].fillna(0).astype(int).values * CARD[f]
        elif f in BINS_PROT:
            o = pd.cut(df[f].fillna(MED[f]), bins=BINS_PROT[f], labels=False, right=False)
            total += (2 - o.fillna(0)).astype(int).values * CARD[f]
        elif f == 'lactate':
            o = pd.cut(df['aniongap'].fillna(MED['aniongap']),
                       bins=[-1, 12, 18, 999], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD['lactate']
        else:
            o = pd.cut(df[f].fillna(MED[f]), bins=BINS_RISK[f], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD[f]
    return total.astype(int)

# ---- eICU exact LM24, staging, within-stage tertiles ----
e = pd.read_csv(DATA + 'cs_eicu_canonical.csv').drop(columns=['aniongap']).rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
e = e.merge(pd.read_csv(SCRATCH + 'eicu_24h_flags.csv'), on='patientunitstayid')
ec = pd.read_csv(DATA + 'eicu_scai_components.csv')
mp = pd.read_csv(DATA + 'eicu_mcs_published.csv')
ec['mcs_pub'] = ec['patientunitstayid'].isin(mp['patientunitstayid']).astype(int)
e = e.merge(ec, on='patientunitstayid')
el = e[e['in_icu_at_24h'] == 1].copy()
yl = el['hosp_mort'].astype(int).values
def stage_e(r):
    if r['arrest_dx'] == 1: return 'E'
    if r['mcs_pub'] == 1: return 'D'
    if r['vaso_count'] > 0 or r['inotrope_flag'] == 1: return 'C'
    return 'B'
el['stage'] = el.apply(stage_e, axis=1)
el['s_ag'] = card_score_ag(el)
print(f"eICU exact LM24 n={len(el)}; stage totals:", el.groupby('stage').size().to_dict())
rows = []
for s in ['B', 'C', 'D', 'E']:
    sub = el[el.stage == s]
    t = pd.qcut(sub['s_ag'], 3, labels=False, duplicates='drop')
    for k, lab in enumerate(['Low', 'Mid', 'High']):
        mk = (t == k)
        yk = sub['hosp_mort'][mk].astype(int)
        wlo, whi = wilson(int(yk.sum()), int(mk.sum()))
        rows.append(dict(cohort='eICU', stage=s, tertile=lab, n=int(mk.sum()),
                         mortality=round(100 * yk.mean(), 1), ci=f"{wlo:.1f}-{whi:.1f}"))
f1e = pd.DataFrame(rows)
for s in ['B', 'C', 'D', 'E']:
    r = f1e[f1e.stage == s]
    print("  " + s + ": " + " | ".join(f"{t} n={n} {m}%" for t, n, m in zip(r.tertile, r.n, r.mortality))
          + f"   spread {r.mortality.iloc[2]-r.mortality.iloc[0]:+.1f}")
f1e.to_csv(OUT + 'figure1_eicu_lm24.csv', index=False)

# ---- DCA data, landmark frame (v2.0 AG vs BOS,MA2 recalibrated) ----
e2 = e.merge(pd.read_csv(SCRATCH + 'eicu_cmp.csv'), on='patientunitstayid', how='left')
el2 = e2[e2['in_icu_at_24h'] == 1].copy()
yl2 = el2['hosp_mort'].astype(int).values
el2['p_ag'] = predict(V2_AG, el2)
bm = ((el2.bun_max >= 25).astype(int) + (el2.spo2_min < 88).astype(int) + (el2.sbp_min < 80).astype(int)
      + (el2.mech_vent == 1).astype(int) + (el2.age >= 60).astype(int) + (el2.aniongap_max >= 14).astype(int)).astype(float)
bm[el2[['bun_max', 'spo2_min', 'sbp_min', 'age', 'aniongap_max']].isna().any(axis=1)] = np.nan
RISK = {0: .005, 1: .014, 2: .039, 3: .10, 4: .235, 5: .46, 6: .702}
cc = el2[bm.notna()].copy(); cc['bm_p'] = bm[bm.notna()].map(RISK)
ycc = cc['hosp_mort'].astype(int).values
lp = np.log(cc['bm_p'] / (1 - cc['bm_p']))
recal = sm.Logit(ycc, sm.add_constant(lp)).fit(disp=0)
cc['bm_recal'] = recal.predict(sm.add_constant(lp))
def nb(p, yv, t): return np.mean((p >= t) * yv) - np.mean((p >= t) * (1 - yv)) * (t / (1 - t))
ths = np.arange(0.05, 0.71, 0.01)
base = ycc.mean()
dca = pd.DataFrame({'threshold': ths})
dca['cs_mort6_ag'] = [nb(cc['p_ag'].values, ycc, t) for t in ths]
dca['bosma2_recal'] = [nb(cc['bm_recal'].values, ycc, t) for t in ths]
dca['bosma2_published'] = [nb(cc['bm_p'].values, ycc, t) for t in ths]
dca['treat_all'] = [base - (1 - base) * (t / (1 - t)) for t in ths]
dca.to_csv(OUT + 'dca_lm24_common.csv', index=False)
print(f"\nDCA (landmark common-scorable n={len(cc)}): net benefit at 20%/40%: "
      f"CS-MORT-6 {nb(cc['p_ag'].values, ycc, .2):.3f}/{nb(cc['p_ag'].values, ycc, .4):.3f}, "
      f"BOS,MA2 recal {nb(cc['bm_recal'].values, ycc, .2):.3f}/{nb(cc['bm_recal'].values, ycc, .4):.3f}")
print("\n[ADDENDUM COMPLETE] figure1_eicu_lm24.csv, dca_lm24_common.csv")
