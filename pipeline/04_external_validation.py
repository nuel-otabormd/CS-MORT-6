"""External validation in eICU, single locked run.

Applies the frozen pipeline once to the eICU 24-hour landmark; also produces
severity-frame continuity estimates, BOS,MA2 comparisons in both frames,
48-hour reapplication, and scorability.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
DATA    = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'
SCRATCH = DATA
OUT     = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
np.random.seed(42)
R = []  # result rows

F6   = ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw']
CONT = ['lactate', 'uo', 'age', 'bun', 'rdw']
CARD = {'lactate': 2, 'uo': 1, 'ohca_arrest': 3, 'age': 1, 'bun': 1, 'rdw': 1}
BINS_RISK = {'lactate': [-1, 2, 4, 999], 'bun': [-1, 25, 45, 9e9],
             'age': [-1, 65, 80, 999], 'rdw': [-1, 14.5, 16, 999]}
BINS_PROT = {'uo': [-1, 0.5, 1.0, 999]}

# ---------------- frozen MIMIC objects (v2.0 on exact LM24; v1.1 on all-comers) ----
dm = pd.read_csv(DATA + 'cs_features_canonical.csv').rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
dm = dm.merge(pd.read_csv(SCRATCH + 'mimic_exact_lm_flags.csv'), on='stay_id')
lmM = dm[dm['exact_lm24'] == 1].reset_index(drop=True)
yM = lmM['in_hospital_mortality'].astype(int).values
yA = dm['in_hospital_mortality'].astype(int).values

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

V2_LAC = fit_frozen(lmM, yM, ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
V2_AG  = fit_frozen(lmM, yM, ['aniongap', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
V11_LAC = fit_frozen(dm, yA, ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
V11_AG  = fit_frozen(dm, yA, ['aniongap', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
MED_LM24 = lmM[CONT + ['aniongap']].median()   # frozen missing-value reference for the card

def card_score(df, ag_for_lactate=False):
    total = np.zeros(len(df))
    for f in F6:
        if f == 'ohca_arrest':
            total += df[f].fillna(0).astype(int).values * CARD[f]
        elif f in BINS_PROT:
            o = pd.cut(df[f].fillna(MED_LM24[f]), bins=BINS_PROT[f], labels=False, right=False)
            total += (2 - o.fillna(0)).astype(int).values * CARD[f]
        elif f == 'lactate' and ag_for_lactate:
            o = pd.cut(df['aniongap'].fillna(MED_LM24['aniongap']),
                       bins=[-1, 12, 18, 999], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD['lactate']
        else:
            o = pd.cut(df[f].fillna(MED_LM24[f]), bins=BINS_RISK[f], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD[f]
    return total.astype(int)

def auc_ci(yv, p, B=2000):
    rng = np.random.default_rng(42); a = []
    for _ in range(B):
        i = rng.integers(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1: a.append(roc_auc_score(yv[i], np.asarray(p)[i]))
    return np.percentile(a, [2.5, 97.5])
def slope_citl(p, yv):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9); lp = np.log(p / (1 - p))
    return (sm.Logit(yv, sm.add_constant(lp)).fit(disp=0).params[1],
            sm.Logit(yv, np.ones(len(yv)), offset=lp).fit(disp=0).params[0])
def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return 100 * (c - hw), 100 * (c + hw)
def row(frame, item, value): R.append(dict(frame=frame, item=item, value=value)); print(f"  {item}: {value}")

# ---------------- eICU data ----------------
e = pd.read_csv(DATA + 'cs_eicu_canonical.csv').drop(columns=['aniongap']).rename(
        columns={'uo_rate_mlkghr': 'uo', 'aniongap_harmonized': 'aniongap'})
e = e.merge(pd.read_csv(SCRATCH + 'eicu_24h_flags.csv'), on='patientunitstayid')
e = e.merge(pd.read_csv(SCRATCH + 'eicu_cmp.csv'), on='patientunitstayid', how='left')
mpg = pd.read_csv(DATA + 'eicu_patient_mapping.csv')
e = e.merge(mpg, on='patientunitstayid', how='left')
e = e.sort_values(['uniquepid', 'uvn', 'phs', 'patientunitstayid']).reset_index(drop=True)
# Amended primary external population (PROTOCOL_AMENDMENT_20260909.md):
# landmark + CS documented by 24 h + first QUALIFYING stay per patient
# (dedup within each eligibility set, rows pre-sorted by uvn/phs/stay id).
dx24 = (e['first_cs_offset'] <= 1440).values
def first_within(mask):
    keep = np.zeros(len(e), bool)
    sub = e.loc[mask, 'uniquepid']
    keep[np.flatnonzero(mask)[~sub.duplicated(keep='first').values]] = True
    return keep
ye = e['hosp_mort'].astype(int).values
LM_ALL = (e['in_icu_at_24h'] == 1).values
LM = first_within(LM_ALL & dx24)          # amended primary
LM_DEDUP = first_within(LM_ALL)           # sensitivity: dedup only
assert LM.sum() == 1047 and ye[LM].sum() == 305, (LM.sum(), ye[LM].sum())

print("=" * 72); print("A. eICU EXACT 24-H LANDMARK, AMENDED PRIMARY (one stay/patient, CS documented by 24 h)")
print("=" * 72)
el = e[LM]; yl = ye[LM]
row('LM24', 'n / deaths / mortality', f"{len(el)} / {yl.sum()} / {100*yl.mean():.1f}%")
row('LM24', 'hospitals contributing', f"{el['hospitalid'].nunique()}")
for m, lab in [(V2_LAC, 'v2.0 lactate'), (V2_AG, 'v2.0 anion gap')]:
    p = predict(m, el); lo, hi = auc_ci(yl, p); sl, ci = slope_citl(p, yl)
    row('LM24', f'{lab} AUROC', f"{roc_auc_score(yl, p):.3f} ({lo:.3f}-{hi:.3f})")
    row('LM24', f'{lab} slope/CITL/Brier', f"{sl:.2f} / {ci:+.3f} / {np.mean((p-yl)**2):.3f}")
p_ag_lm = predict(V2_AG, el)
d_int = sm.Logit(yl, np.ones(len(yl)),
                 offset=np.log(np.clip(p_ag_lm, 1e-9, 1-1e-9) / (1 - np.clip(p_ag_lm, 1e-9, 1-1e-9)))).fit(disp=0).params[0]
row('LM24', 'anion-gap local intercept update (log-odds)', f"{d_int:+.3f}")
s_ag = card_score(el, ag_for_lactate=True)
lo, hi = auc_ci(yl, s_ag)
row('LM24', 'integer card (anion gap) AUROC', f"{roc_auc_score(yl, s_ag):.3f} ({lo:.3f}-{hi:.3f})")
for blo, bhi, lab in [(-1, 3, 'Low 0-3'), (3, 5, 'Moderate 4-5'), (5, 7, 'High 6-7'), (7, 15, 'Very high 8-15')]:
    mk = (s_ag > blo) & (s_ag <= bhi)
    wlo, whi = wilson(int(yl[mk].sum()), int(mk.sum()))
    row('LM24', f'band {lab}', f"n={int(mk.sum())} mortality {100*yl[mk].mean():.1f}% ({wlo:.1f}-{whi:.1f})")
for c, lab in [('lactate', 'lactate'), ('aniongap', 'anion gap'), ('uo', 'urine output'), ('bun', 'BUN'), ('rdw', 'RDW')]:
    row('LM24', f'observed {lab}', f"{100*el[c].notna().mean():.1f}%")
row('LM24', 'all anion-gap-model inputs observed', f"{100*el[['aniongap','uo','bun','rdw','age']].notna().all(axis=1).mean():.1f}%")
row('LM24', 'all lactate-model inputs observed', f"{100*el[['lactate','uo','bun','rdw','age']].notna().all(axis=1).mean():.1f}%")

print("=" * 72); print("A2. SENSITIVITY POPULATIONS (frozen model, unchanged)")
print("=" * 72)
for mk_s, lab_s in [(LM_ALL, 'all landmark stays (n=1,586 frame)'), (LM_DEDUP, 'one stay/patient, any-time documentation')]:
    es = e[mk_s]; ys = ye[mk_s]
    p_s = predict(V2_AG, es); lo_s, hi_s = auc_ci(ys, p_s)
    s_s = card_score(es, ag_for_lactate=True)
    row('LM24_sens', f'{lab_s}', f"n={len(es)} deaths={ys.sum()}; AG {roc_auc_score(ys, p_s):.3f} ({lo_s:.3f}-{hi_s:.3f}); integer {roc_auc_score(ys, s_s):.3f}")
late_arrest = (e['ohca_arrest'] == 1) & (e['first_arrest_offset'] > 1440)
e_za = e.copy(); e_za.loc[late_arrest, 'ohca_arrest'] = 0
row('LM24_sens', 'arrest flags first documented after 24 h (primary)', f"{int((late_arrest & LM).sum())}")
row('LM24_sens', 'primary AG AUROC with late arrests zeroed',
    f"{roc_auc_score(yl, predict(V2_AG, e_za[LM])):.3f}; integer {roc_auc_score(yl, card_score(e_za[LM], ag_for_lactate=True)):.3f}")

print("=" * 72); print("B. eICU ALL-COMERS (day-1 severity frame), v1.1 for continuity")
print("=" * 72)
row('allcomers', 'n / deaths / mortality', f"{len(e)} / {ye.sum()} / {100*ye.mean():.1f}%")
for m, lab in [(V11_LAC, 'v1.1 lactate'), (V11_AG, 'v1.1 anion gap')]:
    p = predict(m, e); lo, hi = auc_ci(ye, p); sl, ci = slope_citl(p, ye)
    row('allcomers', f'{lab} AUROC', f"{roc_auc_score(ye, p):.3f} ({lo:.3f}-{hi:.3f})")
    row('allcomers', f'{lab} slope/CITL', f"{sl:.2f} / {ci:+.3f}")

# ---------------- BOS,MA2 (validated vectorized implementation) ----------------
bm = ((e.bun_max >= 25).astype(int) + (e.spo2_min < 88).astype(int) + (e.sbp_min < 80).astype(int)
      + (e.mech_vent == 1).astype(int) + (e.age >= 60).astype(int) + (e.aniongap_max >= 14).astype(int)).astype(float)
bm[e[['bun_max', 'spo2_min', 'sbp_min', 'age', 'aniongap_max']].isna().any(axis=1)] = np.nan
e['bm'] = bm

def midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]: j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1; i = j
    out = np.empty(N); out[J] = T; return out
def delong(yv, p1, p2):
    yv = np.asarray(yv); pos = yv == 1; neg = yv == 0; m_ = pos.sum(); n_ = neg.sum()
    preds = np.vstack([np.asarray(p1, float), np.asarray(p2, float)])
    tx = np.array([midrank(preds[k][pos]) for k in range(2)])
    ty = np.array([midrank(preds[k][neg]) for k in range(2)])
    tz = np.array([midrank(preds[k]) for k in range(2)])
    aucs = (tz[:, pos].sum(1) - m_ * (m_ + 1) / 2) / (m_ * n_)
    S = np.cov((tz[:, pos] - tx) / n_) / m_ + np.cov(1 - (tz[:, neg] - ty) / m_) / n_
    return aucs, 2 * stats.norm.sf(abs((aucs[0] - aucs[1]) / np.sqrt(S[0, 0] + S[1, 1] - 2 * S[0, 1])))
def h2h(frame, mask, p_model, lab):
    cc = mask & e['bm'].notna().values
    yv = ye[cc]; pa = np.asarray(p_model)[cc]; pb = e['bm'].values[cc]
    _, pv = delong(yv, pa, pb)
    rng = np.random.default_rng(42); diffs = []
    for _ in range(2000):
        i = rng.integers(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1:
            diffs.append(roc_auc_score(yv[i], pa[i]) - roc_auc_score(yv[i], pb[i]))
    row(frame, f'{lab}: n common-scorable', f"{int(cc.sum())} (mortality {100*yv.mean():.1f}%)")
    row(frame, f'{lab}: model vs BOS,MA2', f"{roc_auc_score(yv, pa):.3f} vs {roc_auc_score(yv, pb):.3f}, "
        f"diff {roc_auc_score(yv, pa)-roc_auc_score(yv, pb):+.3f} "
        f"({np.percentile(diffs, 2.5):+.3f} to {np.percentile(diffs, 97.5):+.3f}), DeLong P={pv:.2f}")

print("=" * 72); print("C. BOS,MA2 comparisons")
print("=" * 72)
h2h('allcomers', np.ones(len(e), bool), predict(V11_AG, e), 'all-comers (native frame, v1.1 AG)')
h2h('LM24', LM, predict(V2_AG, e), 'landmark frame (v2.0 AG)')
# imputation-based sensitivity: chained-equations imputation of checklist inputs, all LM24 patients
imp_cols = ['bun_max', 'spo2_min', 'sbp_min', 'age', 'aniongap_max']
imp = IterativeImputer(random_state=42, max_iter=10).fit(e.loc[LM, imp_cols])
ei = pd.DataFrame(imp.transform(e.loc[LM, imp_cols]), columns=imp_cols, index=e.index[LM])
bm_i = ((ei.bun_max >= 25).astype(int) + (ei.spo2_min < 88).astype(int) + (ei.sbp_min < 80).astype(int)
        + (e.loc[LM, 'mech_vent'] == 1).astype(int).values + (ei.age >= 60).astype(int)
        + (ei.aniongap_max >= 14).astype(int))
rng = np.random.default_rng(42); diffs = []
pa = p_ag_lm; pb = bm_i.values
for _ in range(2000):
    i = rng.integers(0, len(yl), len(yl))
    if len(np.unique(yl[i])) > 1:
        diffs.append(roc_auc_score(yl[i], pa[i]) - roc_auc_score(yl[i], pb[i]))
row('LM24', 'imputed BOS,MA2 (all landmark pts) AUROC', f"{roc_auc_score(yl, bm_i):.3f}")
row('LM24', 'v2.0 AG vs imputed BOS,MA2', f"diff {roc_auc_score(yl, pa)-roc_auc_score(yl, bm_i):+.3f} "
    f"({np.percentile(diffs, 2.5):+.3f} to {np.percentile(diffs, 97.5):+.3f})")

print("=" * 72); print("D. eICU 48-H LANDMARK, frozen v2.0")
print("=" * 72)
e48 = pd.read_csv(SCRATCH + 'eicu_48h_clean.csv')
e48 = e48.merge(e[['patientunitstayid', 'lactate', 'uo', 'bun', 'rdw', 'aniongap',
                   'uniquepid', 'uvn', 'phs', 'first_cs_offset']],
                on='patientunitstayid', suffixes=('', '_24h'))
e48 = e48[e48['first_cs_offset'] <= 1440]
e48 = e48.sort_values(['uniquepid', 'uvn', 'phs', 'patientunitstayid'])
e48 = e48[~e48['uniquepid'].duplicated(keep='first')]
l48 = e48[e48['in_icu_48h'] == 1].copy()
y48 = l48['hosp_mort'].astype(int).values
row('LM48', 'n / deaths / mortality', f"{len(l48)} / {y48.sum()} / {100*y48.mean():.1f}%")
upd = l48.rename(columns={'lactate': 'lact24', 'uo': 'uo24', 'bun': 'bun24', 'rdw': 'rdw24', 'aniongap': 'ag24'})\
         .rename(columns={'lactate48': 'lactate', 'uo48': 'uo', 'bun48': 'bun', 'rdw48': 'rdw', 'ag48': 'aniongap'})
for m, lab in [(V2_AG, 'anion gap'), (V2_LAC, 'lactate')]:
    p_u = predict(m, upd); p_s = predict(m, l48)   # updated 48-h vs stale 24-h features
    sl_u, ci_u = slope_citl(p_u, y48); sl_s, ci_s = slope_citl(p_s, y48)
    lo_u, hi_u = auc_ci(y48, p_u)
    row('LM48', f'{lab} updated-48h AUROC', f"{roc_auc_score(y48, p_u):.3f} ({lo_u:.3f}-{hi_u:.3f}), slope {sl_u:.2f}, CITL {ci_u:+.3f}")
    row('LM48', f'{lab} stale-24h AUROC', f"{roc_auc_score(y48, p_s):.3f}, slope {sl_s:.2f}, CITL {ci_s:+.3f}")
for c, lab in [('lactate', 'lactate'), ('uo', 'urine output'), ('bun', 'BUN'), ('rdw', 'RDW'), ('aniongap', 'anion gap')]:
    row('LM48', f'observed {lab} (cumulative)', f"{100*upd[c].notna().mean():.1f}%")
allobs_ag = upd[['aniongap', 'uo', 'bun', 'rdw', 'age']].notna().all(axis=1).mean()
row('LM48', 'all anion-gap-model inputs observed', f"{100*allobs_ag:.1f}%")

pd.DataFrame(R).to_csv(OUT + 'locked_external_results.csv', index=False)
print("\n[LOCKED RUN COMPLETE] outputs/locked_external_results.csv")
