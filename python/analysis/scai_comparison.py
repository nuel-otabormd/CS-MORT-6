import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
np.random.seed(42)

# ---- data: most-recent-value 7 features + SCAI stage variables ----
d  = pd.read_csv('/tmp/feat_mr.csv')
sc = pd.read_csv('/tmp/scai.csv')
d  = d.merge(sc, on='stay_id', how='left')
y  = d['in_hospital_mortality'].astype(int).values
SEVEN = ['lactate','uo_rate_mlkghr','ohca_arrest','age','bun','rdw','bilirubin']
STAGE_MAP = {'A':1,'B':2,'C':3,'D':4,'E':5}
d['stage_ord'] = d['scai_cswg_stage'].map(STAGE_MAP)

cv = StratifiedKFold(5, shuffle=True, random_state=42)

def oof_proba(cols, data=d, yy=y):
    """Out-of-fold predicted risk from the penalized-LR CS-MORT-7 model (leak-safe for comparison)."""
    Z = data[cols].astype(float).copy()
    for c in cols:
        lo,hi = Z[c].quantile(.01), Z[c].quantile(.99); Z[c] = Z[c].clip(lo,hi)
    pipe = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(),
                         LogisticRegression(max_iter=800, C=0.5))
    return cross_val_predict(pipe, Z, yy, cv=cv, method='predict_proba')[:,1]

def auc_ci(yt, sp, B=1000):
    """Bootstrap 95% CI for a single AUROC."""
    rng = np.random.default_rng(42); n=len(yt); a=[]
    yt=np.asarray(yt); sp=np.asarray(sp)
    for _ in range(B):
        i=rng.integers(0,n,n)
        if yt[i].sum() in (0,len(i)): continue
        a.append(roc_auc_score(yt[i], sp[i]))
    return np.percentile(a,2.5), np.percentile(a,97.5)

def auc_diff_test(yt, s1, s2, B=2000):
    """Paired bootstrap: AUROC(s1) - AUROC(s2), 95% CI + 2-sided p (proportion crossing 0)."""
    rng=np.random.default_rng(7); n=len(yt); diffs=[]
    yt=np.asarray(yt); s1=np.asarray(s1); s2=np.asarray(s2)
    for _ in range(B):
        i=rng.integers(0,n,n)
        if yt[i].sum() in (0,len(i)): continue
        diffs.append(roc_auc_score(yt[i],s1[i]) - roc_auc_score(yt[i],s2[i]))
    diffs=np.array(diffs); lo,hi=np.percentile(diffs,[2.5,97.5])
    p = 2*min((diffs<=0).mean(), (diffs>=0).mean())
    return diffs.mean(), lo, hi, p

p7 = oof_proba(SEVEN)
d['p7'] = p7

print("="*72)
print("PART A. SCAI-CSWG stage vs CS-MORT-7 as a DISCRIMINATOR of in-hospital mortality")
print("="*72)
m = d['stage_ord'].notna()
auc_stage = roc_auc_score(y[m.values], d.loc[m,'stage_ord'])
auc_7     = roc_auc_score(y[m.values], d.loc[m,'p7'])
print(f"  n with stage = {m.sum()}, events = {y[m.values].sum()}")
cl,ch = auc_ci(y[m.values], d.loc[m,'stage_ord'])
print(f"  SCAI-CSWG stage (ordinal A-E): AUROC {auc_stage:.3f}  (95% CI {cl:.3f}-{ch:.3f})")
cl,ch = auc_ci(y[m.values], d.loc[m,'p7'])
print(f"  CS-MORT-7 (continuous)       : AUROC {auc_7:.3f}  (95% CI {cl:.3f}-{ch:.3f})")
md,lo,hi,pv = auc_diff_test(y[m.values], d.loc[m,'p7'].values, d.loc[m,'stage_ord'].values)
print(f"  DIFFERENCE (CS-MORT-7 - stage): {md:+.3f}  (95% CI {lo:+.3f} to {hi:+.3f}), p={pv:.4f}")

print()
print("="*72)
print("PART B. WITHIN-STAGE RESOLUTION  (do two same-stage patients differ?)")
print("="*72)
print("  CS-MORT-7 discrimination computed WITHIN each SCAI stage:")
for stg in ['B','C','D','E']:
    s = d[d['scai_cswg_stage']==stg]
    if s['in_hospital_mortality'].nunique()<2: continue
    a = roc_auc_score(s['in_hospital_mortality'], s['p7'])
    print(f"    Stage {stg}: n={len(s):4d}, mort={s['in_hospital_mortality'].mean():.3f}, within-stage AUROC={a:.3f}")
print()
print("  Mortality by CS-MORT-7 tertile WITHIN each stage (shows risk spread the stage misses):")
print(f"    {'Stage':>6} {'n':>5} {'T1(low) mort':>13} {'T2 mort':>9} {'T3(high) mort':>14} {'spread':>7}")
for stg in ['B','C','D','E']:
    s = d[d['scai_cswg_stage']==stg].copy()
    if len(s)<30: continue
    s['tert'] = pd.qcut(s['p7'], 3, labels=[1,2,3], duplicates='drop')
    g = s.groupby('tert')['in_hospital_mortality'].mean()
    if len(g)<3: continue
    spread = g.iloc[-1]-g.iloc[0]
    print(f"    {stg:>6} {len(s):>5} {g.iloc[0]:>13.3f} {g.iloc[1]:>9.3f} {g.iloc[2]:>14.3f} {spread:>7.3f}")

print()
print("="*72)
print("PART C. INCREMENTAL VALUE  (does each add to the other?)")
print("="*72)
dd = d[m].copy(); yy = y[m.values]
# stage as one-hot to be fair to the categorical comparator
stage_oh = pd.get_dummies(dd['scai_cswg_stage'], prefix='stg').astype(float)
def cv_auc(Xframe):
    pipe = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(),
                         LogisticRegression(max_iter=800, C=0.5))
    pr = cross_val_predict(pipe, Xframe, yy, cv=cv, method='predict_proba')[:,1]
    return roc_auc_score(yy, pr), pr
Z7 = dd[SEVEN].astype(float).copy()
for c in SEVEN:
    lo,hi=Z7[c].quantile(.01),Z7[c].quantile(.99); Z7[c]=Z7[c].clip(lo,hi)
a_stage,_  = cv_auc(stage_oh)
a_7, pr7   = cv_auc(Z7)
a_both,prb = cv_auc(pd.concat([Z7.reset_index(drop=True), stage_oh.reset_index(drop=True)], axis=1))
print(f"  SCAI stage (one-hot) alone : CV AUROC {a_stage:.3f}")
print(f"  CS-MORT-7 alone            : CV AUROC {a_7:.3f}")
print(f"  CS-MORT-7 + SCAI stage     : CV AUROC {a_both:.3f}   (delta over CS-MORT-7 = {a_both-a_7:+.3f})")
md,lo,hi,pv = auc_diff_test(yy, prb, pr7)
print(f"    adding stage to CS-MORT-7: {md:+.3f} (95% CI {lo:+.3f} to {hi:+.3f}), p={pv:.4f}")

print()
print("="*72)
print("PART D. TRAJECTORY  (48h landmark: does shock deterioration add to the score?)")
print("="*72)
lm = d[(d['present_at_48h']==1)].copy()
ylm = lm['in_hospital_mortality'].astype(int).values
print(f"  48h-landmark analytic set: n={len(lm)}, events={ylm.sum()}, mort={ylm.mean():.3f}")
# baseline CS-MORT-7 (re-fit OOF within the landmark set), then + dynamic deterioration markers
Zb = lm[SEVEN].astype(float).copy()
for c in SEVEN:
    lo,hi=Zb[c].quantile(.01),Zb[c].quantile(.99); Zb[c]=Zb[c].clip(lo,hi)
dyn = lm[['scai_escalation','vaso_escalation','new_rrt_incident','new_mcs']].fillna(0).astype(float)
ab, prb_ = cv_auc_lm = (lambda X: ( (lambda pr: (roc_auc_score(ylm,pr), pr))(
        cross_val_predict(make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),
        LogisticRegression(max_iter=800,C=0.5)), X, ylm, cv=cv, method='predict_proba')[:,1])))(Zb)
ad, prd_ = (lambda X: ( (lambda pr: (roc_auc_score(ylm,pr), pr))(
        cross_val_predict(make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),
        LogisticRegression(max_iter=800,C=0.5)), X, ylm, cv=cv, method='predict_proba')[:,1])))(
        pd.concat([Zb.reset_index(drop=True), dyn.reset_index(drop=True)],axis=1))
print(f"  CS-MORT-7 (baseline) at 48h           : CV AUROC {ab:.3f}")
print(f"  CS-MORT-7 + deterioration markers     : CV AUROC {ad:.3f}   (delta = {ad-ab:+.3f})")
md,lo,hi,pv = auc_diff_test(ylm, prd_, prb_)
print(f"    adding deterioration: {md:+.3f} (95% CI {lo:+.3f} to {hi:+.3f}), p={pv:.4f}")
# mortality by escalation within baseline-risk tertiles (cross-classification)
lm['rt'] = pd.qcut(prb_, 3, labels=['low','mid','high'])
print("\n  Mortality cross-classified by baseline CS-MORT-7 risk tertile x 48h escalation:")
ct = lm.pivot_table(index='rt', columns='scai_escalation', values='in_hospital_mortality', aggfunc='mean')
print(ct.round(3).to_string())
