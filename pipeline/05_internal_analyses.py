"""Internal analyses (MIMIC-IV).

Exact 48-hour landmark reassessment, score trajectory, event timing,
collinearity, imputation and cohort sensitivity analyses, fairness subgroups,
influence-function intervals, and SCAI incremental value.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
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
d = d.merge(pd.read_csv(SCRATCH + 'mimic_exact_lm_flags.csv'), on='stay_id')
lm = d[d['exact_lm24'] == 1].reset_index(drop=True)
y = lm['in_hospital_mortality'].astype(int).values
MED = lm[CONT + ['aniongap']].median()

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
def slope_citl(p, yv):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9); lp = np.log(p / (1 - p))
    return (sm.Logit(yv, sm.add_constant(lp)).fit(disp=0).params[1],
            sm.Logit(yv, np.ones(len(yv)), offset=lp).fit(disp=0).params[0])
def auc_ci(yv, p, B=2000):
    rng = np.random.default_rng(42); a = []
    for _ in range(B):
        i = rng.integers(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1: a.append(roc_auc_score(yv[i], np.asarray(p)[i]))
    return np.percentile(a, [2.5, 97.5])
def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return 100 * (c - hw), 100 * (c + hw)
def card_score(df, med, drop_ohca=False, nonstaging=False):
    total = np.zeros(len(df))
    for f in F6:
        if nonstaging and f in ('lactate', 'ohca_arrest'): continue
        if drop_ohca and f == 'ohca_arrest': continue
        if f == 'ohca_arrest':
            total += df[f].fillna(0).astype(int).values * CARD[f]
        elif f in BINS_PROT:
            o = pd.cut(df[f].fillna(med[f]), bins=BINS_PROT[f], labels=False, right=False)
            total += (2 - o.fillna(0)).astype(int).values * CARD[f]
        else:
            o = pd.cut(df[f].fillna(med[f]), bins=BINS_RISK[f], labels=False, right=False)
            total += o.fillna(0).astype(int).values * CARD[f]
    return total.astype(int)

V2_LAC = fit_frozen(lm, y, ['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
V2_AG  = fit_frozen(lm, y, ['aniongap', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'])
RES = []
def row(sec, item, value): RES.append(dict(section=sec, item=item, value=value)); print(f"  {item}: {value}")

# ============ 1+2. MIMIC exact 48-h landmark + symmetric trajectory ============
print("=" * 70); print("1. MIMIC EXACT 48-H LANDMARK (frozen v2.0)"); print("=" * 70)
h = pd.read_csv(SCRATCH + 'horizon_mr.csv').rename(columns={'uo_rate': 'uo'})
h48 = h[h.horizon_h == 48][['stay_id', 'lactate', 'uo', 'bun', 'rdw']]
lm48 = d[d['exact_lm48'] == 1][['stay_id', 'in_hospital_mortality', 'ohca_arrest', 'age',
                                'lactate', 'uo', 'bun', 'rdw']]
mrg = lm48.merge(h48, on='stay_id', suffixes=('_24', ''))
y48 = mrg['in_hospital_mortality'].astype(int).values
row('lm48', 'n / deaths / mortality', f"{len(mrg)} / {y48.sum()} / {100*y48.mean():.1f}%")
stale = mrg.rename(columns={'lactate': 'l48', 'uo': 'u48', 'bun': 'b48', 'rdw': 'r48'})\
           .rename(columns={'lactate_24': 'lactate', 'uo_24': 'uo', 'bun_24': 'bun', 'rdw_24': 'rdw'})
p_up = predict(V2_LAC, mrg); p_st = predict(V2_LAC, stale)
for p, lab in [(p_up, 'updated-48h'), (p_st, 'stale-24h')]:
    sl, ci = slope_citl(p, y48); lo, hi = auc_ci(y48, p)
    row('lm48', f'continuous lactate {lab}', f"AUROC {roc_auc_score(y48, p):.3f} ({lo:.3f}-{hi:.3f}), slope {sl:.2f}, CITL {ci:+.3f}")
s24 = card_score(stale, MED); s48 = card_score(mrg, MED)
row('lm48', 'integer stale vs updated AUROC', f"{roc_auc_score(y48, s24):.3f} vs {roc_auc_score(y48, s48):.3f}")

print("=" * 70); print("2. SYMMETRIC TRAJECTORY + archived aOR generator"); print("=" * 70)
delta = s48 - s24
traj_rows = []
for scope, mask in [('all 48-h landmark', np.ones(len(mrg), bool)),
                    ('intermediate 24-h score 4-7', (s24 >= 4) & (s24 <= 7))]:
    for lab, mk in [('Improved (<0)', delta < 0), ('Unchanged (=0)', delta == 0), ('Worsened (>0)', delta > 0)]:
        m2 = mask & mk; k, n = int(y48[m2].sum()), int(m2.sum())
        wlo, whi = wilson(k, n)
        traj_rows.append(dict(scope=scope, group=lab, n=n, mortality=round(100 * k / n, 1),
                              ci=f"{wlo:.1f}-{whi:.1f}"))
        row('trajectory', f'{scope} | {lab}', f"n={n} mortality {100*k/n:.1f}% ({wlo:.1f}-{whi:.1f})")
pd.DataFrame(traj_rows).to_csv(OUT + 'trajectory_symmetric.csv', index=False)
X = sm.add_constant(np.column_stack([s24, delta]).astype(float))
fit = sm.Logit(y48, X).fit(disp=0)
orv = np.exp(fit.params[2]); ci_or = np.exp(fit.conf_int()[2])
row('trajectory', 'aOR per +1 change (adj 24-h score)', f"{orv:.2f} ({ci_or[0]:.2f}-{ci_or[1]:.2f}), p={fit.pvalues[2]:.1e}")

# ============ 3. exact event-time table ============
print("=" * 70); print("3. EVENT-TIME DISTRIBUTION (exact timestamps)"); print("=" * 70)
et = pd.read_csv(SCRATCH + 'mimic_event_time.csv')
row('event-time', 'buckets 0-6/6-12/12-24/24-48h', f"{int(et.d_0_6[0])}/{int(et.d_6_12[0])}/{int(et.d_12_24[0])}/{int(et.d_24_48[0])}")
row('event-time', '48h-7d / >7d', f"{int(et.d_48_168[0])} / {int(et.d_gt168[0])}")
row('event-time', 'anomalies (disclosed)', f"{int(et.death_before_icu[0])} recorded before ICU admission, {int(et.death_no_timestamp[0])} without timestamp")
et.to_csv(OUT + 'event_time_exact.csv', index=False)

# ============ 4. correlations + VIF ============
print("=" * 70); print("4. CORRELATIONS AND VIF (exact LM24)"); print("=" * 70)
for cols, lab in [(['lactate', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'], 'lactate model'),
                  (['aniongap', 'uo', 'ohca_arrest', 'age', 'bun', 'rdw'], 'anion-gap model')]:
    X = lm[cols].astype(float)
    Xw = X.clip(X.quantile(.01), X.quantile(.99), axis=1); Xi = Xw.fillna(Xw.median())
    vifs = {}
    for c in cols:
        others = [o for o in cols if o != c]
        r2 = sm.OLS(Xi[c], sm.add_constant(Xi[others])).fit().rsquared
        vifs[c] = 1 / (1 - r2)
    row('vif', lab, "  ".join(f"{c} {v:.2f}" for c, v in vifs.items()))
corr = lm[['lactate', 'aniongap', 'uo', 'age', 'bun', 'rdw']].corr(method='pearson').round(2)
corr.to_csv(OUT + 'correlation_matrix_lm24.csv')
row('vif', 'key Pearson r', f"lactate-bun {corr.loc['lactate','bun']}, lactate-rdw {corr.loc['lactate','rdw']}, bun-rdw {corr.loc['bun','rdw']}, aniongap-bun {corr.loc['aniongap','bun']}")

# ============ 5. MICE vs median ============
print("=" * 70); print("5. MICE VS MEDIAN (v2.0 lactate, 5-fold CV)"); print("=" * 70)
def cv_auc(imp_kind):
    Xc = lm[['lactate'] + ['uo', 'ohca_arrest', 'age', 'bun', 'rdw']].astype(float)
    Xc = Xc.clip(Xc.quantile(.01), Xc.quantile(.99), axis=1)
    pp = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(Xc, y):
        im = IterativeImputer(random_state=42, max_iter=10, sample_posterior=True) \
             if imp_kind == 'mice' else SimpleImputer(strategy='median')
        md = Pipeline([('i', im), ('s', StandardScaler()),
                       ('l', LogisticRegression(max_iter=800, C=0.5))]).fit(Xc.iloc[tr], y[tr])
        pp[te] = md.predict_proba(Xc.iloc[te])[:, 1]
    sl, ci = slope_citl(pp, y)
    return roc_auc_score(y, pp), sl, ci
for kind in ['median', 'mice']:
    a, sl, ci = cv_auc(kind)
    row('imputation', kind, f"AUROC {a:.3f}, slope {sl:.2f}, CITL {ci:+.3f}")

# ============ 6. sensitivity cohorts (exact LM24) ============
print("=" * 70); print("6. SENSITIVITY COHORTS (frozen v2.0 lactate OOF)"); print("=" * 70)
oofp = pd.read_csv(SCRATCH + 'v2_oof_predictions.csv')
assert (oofp['y'].values == y).all()
p_oof = oofp['oof_lac'].values; s_card = card_score(lm, MED)
for lab, mask in [('ICD-confirmed only', lm['has_cs_icd'] == 1),
                  ('Sepsis-3 excluded', lm['sepsis3'] == 0),
                  ('non-OHCA subgroup', lm['ohca_arrest'] == 0)]:
    mk = mask.values
    a = roc_auc_score(y[mk], p_oof[mk]); ai = roc_auc_score(y[mk], s_card[mk])
    row('sensitivity', lab, f"n={mk.sum()} mort {100*y[mk].mean():.1f}% cont {a:.3f} integer {ai:.3f}")
s_no_ohca = card_score(lm, MED, drop_ohca=True)
row('sensitivity', 'OHCA-free score (all LM24)', f"cont n/a integer {roc_auc_score(y, s_no_ohca):.3f}")

# ============ 7. fairness subgroups ============
print("=" * 70); print("7. FAIRNESS SUBGROUPS (exact LM24, v2.0 lactate OOF)"); print("=" * 70)
demo = pd.read_csv(DATA + 'mimic_demographics.csv')
lmd = lm.merge(demo, on='stay_id', how='left')
frows = []
for col, groups in [('gender', ['M', 'F']), ('race_group', ['White', 'Black', 'Hispanic', 'Asian', 'Other/Unknown'])]:
    for g in groups:
        mk = (lmd[col] == g).values
        if mk.sum() < 40: continue
        a = roc_auc_score(y[mk], p_oof[mk]); lo, hi = auc_ci(y[mk], p_oof[mk])
        sl, ci = slope_citl(p_oof[mk], y[mk])
        frows.append(dict(subgroup=g, n=int(mk.sum()), deaths=int(y[mk].sum()),
                          auroc=round(a, 3), ci=f"{lo:.3f}-{hi:.3f}", slope=round(sl, 2), citl=round(ci, 3)))
        row('fairness', g, f"n={mk.sum()} deaths={y[mk].sum()} AUROC {a:.3f} ({lo:.3f}-{hi:.3f}) slope {sl:.2f} CITL {ci:+.3f}")
pd.DataFrame(frows).to_csv(OUT + 'fairness_subgroups_lm24.csv', index=False)

# ============ 8. cvAUC influence-function CI ============
print("=" * 70); print("8. LEDELL INFLUENCE-FUNCTION CI FOR CV AUROC"); print("=" * 70)
folds = oofp['fold'].values
ics = np.zeros(len(y))
auc_folds = []
for v in np.unique(folds):
    mk = folds == v
    pv, yv = p_oof[mk], y[mk]
    pos, neg = pv[yv == 1], pv[yv == 0]
    a_v = roc_auc_score(yv, pv); auc_folds.append(a_v)
    p1 = yv.mean(); p0 = 1 - p1
    s0 = np.array([(np.sum(neg < x) + 0.5 * np.sum(neg == x)) / len(neg) for x in pv])
    s1 = np.array([(np.sum(pos > x) + 0.5 * np.sum(pos == x)) / len(pos) for x in pv])
    ic = np.where(yv == 1, (s0 - a_v) / p1, (s1 - a_v) / p0)
    ics[mk] = ic
cv_auc_hat = np.mean(auc_folds)
se = np.sqrt(np.var(ics) / len(y))
row('cvauc', 'CV AUROC (fold mean) with IC-based 95% CI',
    f"{cv_auc_hat:.4f} ({cv_auc_hat-1.96*se:.4f}-{cv_auc_hat+1.96*se:.4f}); pooled bootstrap for comparison {roc_auc_score(y,p_oof):.4f} ({auc_ci(y,p_oof)[0]:.4f}-{auc_ci(y,p_oof)[1]:.4f})")

# ============ 9. SCAI incremental value ============
print("=" * 70); print("9. SCAI INCREMENTAL VALUE (exact LM24)"); print("=" * 70)
sc = pd.read_csv(DATA + 'scai_components_mimic.csv')
lms = lm.merge(sc, on='stay_id', suffixes=('', '_sc'))
sup = lms['pressor_count'] + lms['inotrope_flag']; lac_mx = lms['lactate_max']; mcs = lms['mcs_24h_count']
hypo = (lms['sbp_min'] < 90) | (lms['mbp_min'] < 65); oh = lms['ohca_arrest']
def stage(i):
    if oh.iloc[i] == 1 or sup.iloc[i] >= 3 or mcs.iloc[i] >= 2: return 4
    if sup.iloc[i] == 2 or mcs.iloc[i] >= 1 or (lac_mx.iloc[i] > 4 and sup.iloc[i] >= 1): return 3
    if sup.iloc[i] >= 1 or (lac_mx.iloc[i] >= 2 and hypo.iloc[i]): return 2
    if hypo.iloc[i] or (lac_mx.iloc[i] >= 2): return 1
    return 0
stg = np.array([stage(i) for i in range(len(lms))])
s_full = card_score(lms, MED)
m_stage = sm.Logit(y, sm.add_constant(stg.astype(float))).fit(disp=0)
m_score = sm.Logit(y, sm.add_constant(s_full.astype(float))).fit(disp=0)
m_both  = sm.Logit(y, sm.add_constant(np.column_stack([stg, s_full]).astype(float))).fit(disp=0)
lrt = 2 * (m_both.llf - m_stage.llf); p_lrt = stats.chi2.sf(lrt, 1)
a_stage = roc_auc_score(y, m_stage.predict()); a_score = roc_auc_score(y, s_full)
a_both = roc_auc_score(y, m_both.predict())
rng = np.random.default_rng(42); dd = []
pb_stage = m_stage.predict(); pb_both = m_both.predict()
for _ in range(2000):
    i = rng.integers(0, len(y), len(y))
    if len(np.unique(y[i])) > 1:
        dd.append(roc_auc_score(y[i], pb_both[i]) - roc_auc_score(y[i], pb_stage[i]))
row('scai', 'stage-only / score-only / stage+score AUROC', f"{a_stage:.3f} / {a_score:.3f} / {a_both:.3f}")
row('scai', 'LRT score over stage', f"chi2 {lrt:.1f}, p {p_lrt:.1e}")
row('scai', 'paired dAUROC (stage+score - stage)', f"{np.mean(dd):+.3f} ({np.percentile(dd,2.5):+.3f} to {np.percentile(dd,97.5):+.3f})")
LET = {1: 'B', 2: 'C', 3: 'D', 4: 'E'}
f1 = []
for code, sname in LET.items():
    mk = stg == code
    sub_s = s_full[mk]; sub_y = y[mk]
    if mk.sum() < 30: continue
    t = pd.qcut(pd.Series(sub_s), 3, labels=False, duplicates='drop')
    wa = roc_auc_score(sub_y, sub_s)
    walo, wahi = auc_ci(sub_y, sub_s)
    row('scai', f'stage {sname} within-stage AUROC', f"n={mk.sum()} {wa:.3f} ({walo:.3f}-{wahi:.3f})")
    for k, lab in enumerate(['Low', 'Mid', 'High']):
        mk2 = (t == k).values
        klo, khi = wilson(int(sub_y[mk2].sum()), int(mk2.sum()))
        f1.append(dict(cohort='MIMIC', stage=sname, tertile=lab, n=int(mk2.sum()),
                       mortality=round(100 * sub_y[mk2].mean(), 1), ci=f"{klo:.1f}-{khi:.1f}"))
# OHCA-free and non-staging variants within stage
vrows = []
for variant, kw in [('ohca-free', dict(drop_ohca=True)), ('non-staging', dict(nonstaging=True))]:
    sv = card_score(lms, MED, **kw)
    spreads = []
    for code, sname in LET.items():
        mk = stg == code
        if mk.sum() < 30: continue
        t = pd.qcut(pd.Series(sv[mk]), 3, labels=False, duplicates='drop')
        mr = [100 * y[mk][(t == k).values].mean() for k in range(3)]
        spreads.append(f"{sname} {mr[0]:.0f}/{mr[1]:.0f}/{mr[2]:.0f}")
        for k, lab in enumerate(['Low', 'Mid', 'High']):
            mk2 = (t == k).values
            vlo, vhi = wilson(int(y[mk][mk2].sum()), int(mk2.sum()))
            vrows.append(dict(variant=variant, stage=sname, tertile=lab, n=int(mk2.sum()),
                              mortality=round(100 * y[mk][mk2].mean(), 1), ci=f"{vlo:.1f}-{vhi:.1f}"))
    row('scai', f'{variant} tertile mortality by stage', "; ".join(spreads))
pd.DataFrame(f1).to_csv(OUT + 'figure1_mimic_lm24.csv', index=False)
pd.DataFrame(vrows).to_csv(OUT + 'figure1_variants_mimic.csv', index=False)

# ============ 11. availability by horizon ============
print("=" * 70); print("11. AVAILABILITY BY HORIZON (MIMIC, in-ICU patients)"); print("=" * 70)
avail = []
for T in [6, 12, 24, 48]:
    g = h[(h.horizon_h == T) & (h.alive_at_T == 1)]
    r = dict(horizon=T, n=len(g))
    for v in ['lactate', 'bun', 'rdw', 'uo']:
        r[v] = round(100 * g[v].notna().mean(), 1)
    avail.append(r)
    row('availability', f'{T}h (n={len(g)})', "  ".join(f"{v} {r[v]}%" for v in ['lactate', 'bun', 'rdw', 'uo']))
pd.DataFrame(avail).to_csv(OUT + 'availability_by_horizon_mimic.csv', index=False)

pd.DataFrame(RES).to_csv(OUT + 'internal_final_results.csv', index=False)
print("\n[STAGE 05 COMPLETE] outputs/internal_final_results.csv + section CSVs")
