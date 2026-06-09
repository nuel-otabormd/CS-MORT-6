import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, brier_score_loss
np.random.seed(42)

# ---------------------------------------------------------------------------
# FROZEN external validation: train the ENTIRE pipeline on MIMIC (clip bounds,
# imputation medians, scaler, LR coefficients all fit on MIMIC), then apply
# UNCHANGED to eICU. Three acid-base variants: lactate / anion gap / bicarbonate.
# ---------------------------------------------------------------------------
mim = pd.read_csv('/tmp/mimic_variants.csv')          # MIMIC most-recent, primary cohort
eic = pd.read_csv('/tmp/eicu.csv')
mim = mim.rename(columns={'uo_rate_mlkghr':'uo'})
eic = eic.rename(columns={'uo_rate_mlkghr':'uo'})
COMMON = ['uo','ohca_arrest','age','bun','rdw','bilirubin']
ym = mim['in_hospital_mortality'].astype(int).values
ye = eic['hosp_mort'].astype(int).values

class Frozen:
    """Clip(MIMIC bounds) -> median impute(MIMIC) -> scale(MIMIC) -> LR(MIMIC). Frozen on MIMIC."""
    def __init__(self, cols): self.cols = cols
    def fit(self, df, y):
        X = df[self.cols].astype(float).copy()
        self.lo = X.quantile(.01); self.hi = X.quantile(.99)
        X = X.clip(self.lo, self.hi, axis=1)
        self.imp = SimpleImputer(strategy='median').fit(X)
        Xi = self.imp.transform(X)
        self.sc = StandardScaler().fit(Xi)
        self.lr = LogisticRegression(max_iter=800, C=0.5).fit(self.sc.transform(Xi), y)
        return self
    def proba(self, df):
        X = df[self.cols].astype(float).copy().clip(self.lo, self.hi, axis=1)
        return self.lr.predict_proba(self.sc.transform(self.imp.transform(X)))[:,1]

def auc_ci(y, p, B=2000):
    rng = np.random.default_rng(42); n=len(y); a=[]
    y=np.asarray(y); p=np.asarray(p)
    for _ in range(B):
        i=rng.integers(0,n,n)
        if y[i].sum() in (0,len(i)): continue
        a.append(roc_auc_score(y[i],p[i]))
    return np.percentile(a,2.5), np.percentile(a,97.5)

def calib(y, p):
    """CITL (mean obs vs mean pred), recalibration intercept alpha & slope beta, Brier."""
    eps=1e-6; lp = np.log(np.clip(p,eps,1-eps)/(1-np.clip(p,eps,1-eps)))
    # slope beta: y ~ logit(p); intercept-at-slope for CITL: y ~ offset(logit p)
    import statsmodels.api as sm
    slope_m = sm.Logit(y, sm.add_constant(lp)).fit(disp=0)
    citl_m  = sm.Logit(y, np.ones_like(y), offset=lp).fit(disp=0)
    return dict(obs=y.mean(), pred=p.mean(),
                citl=float(citl_m.params[0]), slope=float(slope_m.params[1]),
                brier=brier_score_loss(y,p))

def report(name, cols, sens=False):
    e = eic[eic['obj_ge1']==1] if sens else eic
    yy = ye[eic['obj_ge1'].values==1] if sens else ye
    fr = Frozen(cols).fit(mim, ym)
    p_all = fr.proba(e)
    # complete-case = all variant features observed in eICU
    cc = e[cols].notna().all(axis=1).values
    auc_all = roc_auc_score(yy, p_all); lo,hi = auc_ci(yy, p_all)
    c = calib(yy, p_all)
    scor = cc.mean()
    print(f"\n  {name}  (n={len(e)}{' [obj>=1 sens]' if sens else ''}, events={yy.sum()})")
    print(f"    Fraction fully scorable (all features observed): {scor:.3f}")
    print(f"    FROZEN  AUROC {auc_all:.3f} (95% CI {lo:.3f}-{hi:.3f}) | "
          f"obs {c['obs']:.3f} pred {c['pred']:.3f} | CITL {c['citl']:+.3f} slope {c['slope']:.3f} | Brier {c['brier']:.3f}")
    if cc.sum() > 50 and yy[cc].sum() > 5:
        auc_cc = roc_auc_score(yy[cc], p_all[cc]); lo2,hi2 = auc_ci(yy[cc], p_all[cc])
        print(f"    COMPLETE-CASE (n={cc.sum()})  AUROC {auc_cc:.3f} (95% CI {lo2:.3f}-{hi2:.3f})")
    return p_all, yy, c

print("="*74)
print("MIMIC internal (apparent, frozen pipeline refit) for reference:")
for ab,nm in [('lactate','lactate'),('aniongap','anion gap'),('bicarbonate','bicarbonate')]:
    fr=Frozen([ab]+COMMON).fit(mim,ym); print(f"    CS-MORT-7-{nm:11s} MIMIC apparent AUROC {roc_auc_score(ym,fr.proba(mim)):.3f}")

print("\n" + "="*74)
print("eICU EXTERNAL VALIDATION (frozen MIMIC model) — PRIMARY cohort (diagnosisstring-only)")
print("="*74)
report("CS-MORT-7-AG (anion gap)  [PRIMARY external/deployable]", ['aniongap']+COMMON)
report("CS-MORT-7 (lactate)       [primary MIMIC model]",        ['lactate']+COMMON)
report("CS-MORT-7-bicarbonate     [max-coverage sensitivity]",   ['bicarbonate']+COMMON)

print("\n" + "="*74)
print("SENSITIVITY: harmonized cohort (diagnosisstring + >=1 objective criterion)")
print("="*74)
report("CS-MORT-7-AG (anion gap)", ['aniongap']+COMMON, sens=True)

print("\n" + "="*74)
print("RECALIBRATION (logistic, eICU) — AG variant, primary cohort")
print("="*74)
fr = Frozen(['aniongap']+COMMON).fit(mim, ym); p = fr.proba(eic)
import statsmodels.api as sm
eps=1e-6; lp=np.log(np.clip(p,eps,1-eps)/(1-np.clip(p,eps,1-eps)))
rc = sm.Logit(ye, sm.add_constant(lp)).fit(disp=0)
p_recal = rc.predict(sm.add_constant(lp))
c2 = calib(ye, p_recal)
print(f"  recalibrated: intercept {rc.params[0]:+.3f}, slope {rc.params[1]:.3f}")
print(f"  after recalibration: obs {c2['obs']:.3f} pred {c2['pred']:.3f} | CITL {c2['citl']:+.3f} slope {c2['slope']:.3f} | Brier {c2['brier']:.3f}")

print("\n" + "="*74)
print("RISK-STRATUM table (AG variant, frozen) — relative strata, observed mortality by quintile")
print("="*74)
eic2 = eic.copy(); eic2['p']=p; eic2['q']=pd.qcut(p,5,labels=['Q1(low)','Q2','Q3','Q4','Q5(high)'])
g = eic2.groupby('q').agg(n=('hosp_mort','size'), pred_mean=('p','mean'), obs_mort=('hosp_mort','mean'))
print(g.round(3).to_string())
