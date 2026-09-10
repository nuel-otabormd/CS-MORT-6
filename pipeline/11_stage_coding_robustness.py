"""Stage-coding and refit robustness for the incremental-value analyses.
Reuses pipeline code verbatim (sliced exec) so populations, frozen scores,
and OOF predictions are exactly those of the published analysis.
Sensitivities: (1) SCAI stage as unordered categories (dummies) instead of
one linear ordinal term; (2) bootstrap CIs with the stage-only and
stage+score models REFIT inside every resample. Nothing written to outputs/.
"""
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy import stats
from sklearn.metrics import roc_auc_score

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
PIPE = _B + '/'
OUT = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'

def cat_dummies(svals):
    return pd.get_dummies(pd.Categorical(svals)).astype(float).values[:, 1:]

def sens(yv, stg_int, score_v, tag, nboot=2000):
    yv = np.asarray(yv); stg_int = np.asarray(stg_int).astype(int)
    score_v = np.asarray(score_v, dtype=float)
    # linear published-style fits (for reference within same frame)
    m_sl = sm.Logit(yv, sm.add_constant(stg_int.astype(float))).fit(disp=0)
    m_bl = sm.Logit(yv, sm.add_constant(np.column_stack([stg_int.astype(float), score_v]))).fit(disp=0)
    a_sl = roc_auc_score(yv, m_sl.predict()); a_bl = roc_auc_score(yv, m_bl.predict())
    # categorical fits
    Dc = cat_dummies(stg_int)
    m_sc = sm.Logit(yv, sm.add_constant(Dc)).fit(disp=0)
    m_bc = sm.Logit(yv, sm.add_constant(np.column_stack([Dc, score_v]))).fit(disp=0)
    a_sc = roc_auc_score(yv, m_sc.predict()); a_bc = roc_auc_score(yv, m_bc.predict())
    lrt_c = 2 * (m_bc.llf - m_sc.llf); p_c = stats.chi2.sf(lrt_c, 1)
    # refit bootstrap for both codings
    rng = np.random.default_rng(42)
    d_lin, d_cat, fail = [], [], 0
    n = len(yv)
    for _ in range(nboot):
        i = rng.integers(0, n, n)
        yi = yv[i]
        if len(np.unique(yi)) < 2: continue
        si = stg_int[i]; sv = score_v[i]
        try:
            msl = sm.Logit(yi, sm.add_constant(si.astype(float))).fit(disp=0)
            mbl = sm.Logit(yi, sm.add_constant(np.column_stack([si.astype(float), sv]))).fit(disp=0)
            d_lin.append(roc_auc_score(yi, mbl.predict()) - roc_auc_score(yi, msl.predict()))
            Di = cat_dummies(si)
            msc = sm.Logit(yi, sm.add_constant(Di)).fit(disp=0)
            mbc = sm.Logit(yi, sm.add_constant(np.column_stack([Di, sv]))).fit(disp=0)
            d_cat.append(roc_auc_score(yi, mbc.predict()) - roc_auc_score(yi, msc.predict()))
        except Exception:
            fail += 1
    print(f"\n== {tag} ==")
    print(f"  stage counts: {dict(pd.Series(stg_int).value_counts().sort_index())}")
    print(f"  LINEAR  stage {a_sl:.3f} both {a_bl:.3f}  d={a_bl-a_sl:+.3f}  refit-CI ({np.percentile(d_lin,2.5):+.3f} to {np.percentile(d_lin,97.5):+.3f})")
    print(f"  CATEG   stage {a_sc:.3f} both {a_bc:.3f}  d={a_bc-a_sc:+.3f}  refit-CI ({np.percentile(d_cat,2.5):+.3f} to {np.percentile(d_cat,97.5):+.3f})  LRT chi2 {lrt_c:.1f} p={p_c:.1e}")
    print(f"  boot resamples used lin/cat: {len(d_lin)}/{len(d_cat)}, failures {fail}")
    return dict(tag=tag, a_stage_lin=a_sl, a_both_lin=a_bl, a_stage_cat=a_sc, a_both_cat=a_bc,
                d_lin=a_bl-a_sl, d_lin_lo=np.percentile(d_lin,2.5), d_lin_hi=np.percentile(d_lin,97.5),
                d_cat=a_bc-a_sc, d_cat_lo=np.percentile(d_cat,2.5), d_cat_hi=np.percentile(d_cat,97.5),
                lrt_cat=lrt_c, p_cat=p_c)

RES = []

# ---------------- MIMIC (internal, exact LM24) ----------------
src5 = open(PIPE + '05_internal_analyses.py').read()
partA = src5.split('# ============ 1+2.')[0]
partC = src5.split('# ============ 9. SCAI incremental value ============')[1].split("LET = {1: 'B'")[0]
gl = {'__file__': PIPE + '05_internal_analyses.py'}
exec(compile(partA, '05_partA', 'exec'), gl)
gl['oofp'] = pd.read_csv(gl['SCRATCH'] + 'v2_oof_predictions.csv')
assert (gl['oofp']['y'].values == gl['y']).all()
if 'row' not in gl:
    gl['row'] = lambda sec, item, val: print(f"   [{sec}] {item}: {val}")
exec(compile('# ============ 9. SCAI incremental value ============' + partC, '05_partC', 'exec'), gl)
y_m = gl['y']; stg_m = gl['stg'].astype(int); lp_ag_m = gl['lp_ag']; s_full_m = np.asarray(gl['s_full'])
stg_na_m = gl['stg_na5'].astype(int)
# stage A (0) n=8, 0 deaths: merged into B for categorical coding (noted in report)
stg_m_merged = np.where(stg_m == 0, 1, stg_m)
mort = pd.DataFrame({'stage': stg_m, 'y': y_m}).groupby('stage')['y'].agg(['size', 'mean'])
print('\nMIMIC stage mortality:\n', (mort['mean']*100).round(1).to_string())
RES.append(sens(y_m, stg_m_merged, lp_ag_m, 'MIMIC continuous AG (OOF), stage A merged into B'))
RES.append(sens(y_m, stg_m_merged, s_full_m.astype(float), 'MIMIC integer card, stage A merged into B'))
RES.append(sens(y_m, np.where(stg_na_m==0,1,stg_na_m), lp_ag_m, 'MIMIC continuous AG, no-arrest-rule stage'))

# ---------------- eICU (external, amended primary) ----------------
src6 = open(PIPE + '06_external_descriptive.py').read()
part6 = src6.split('# ---- Within-stage cells')[0]
g6 = {'__file__': PIPE + '06_external_descriptive.py'}
exec(compile(part6, '06_part', 'exec'), g6)
yl = np.asarray(g6['yl']); stg_e = g6['el']['stage'].map({'B':1,'C':2,'D':3,'E':4}).values.astype(int)
lp_el = g6['lp_el']; s_hyb = np.asarray(g6['s_hyb'], dtype=float)
mort_e = pd.DataFrame({'stage': stg_e, 'y': yl}).groupby('stage')['y'].agg(['size', 'mean'])
print('\neICU stage mortality:\n', (mort_e['mean']*100).round(1).to_string())
_LET = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E'}
pd.DataFrame([dict(cohort=c, stage=_LET.get(int(i), str(i)), n=int(r['size']),
                   mortality=round(100 * r['mean'], 1))
              for c, m in (('MIMIC-IV', mort), ('eICU', mort_e))
              for i, r in m.iterrows()]) \
  .to_csv(OUT + 'stage_mortality.csv', index=False)
RES.append(sens(yl, stg_e, lp_el, 'eICU continuous AG (frozen)'))
RES.append(sens(yl, stg_e, s_hyb, 'eICU integer card (deployment rule)'))

pd.DataFrame(RES).to_csv(OUT + 'stage_coding_robustness.csv', index=False)
print('\nDONE')
