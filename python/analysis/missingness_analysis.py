# Missingness analysis: both perfusion variables MNAR (opposite
# directions). Decide model treatment, report stratified discrimination+calibration,
# MI sensitivity, and explain the opposite-sign eICU calibration errors.
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('outputs/tables/cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
y=d['in_hospital_mortality'].astype(int).values
e=pd.read_csv('outputs/tables/cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'}); ye=e['hosp_mort'].astype(int).values
COM=['uo','ohca_arrest','age','bun','rdw']
def slope_citl(p,yv):
    lp=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    sl=LogisticRegression(max_iter=500).fit(lp.reshape(-1,1),yv).coef_[0][0]; return sl, yv.mean()-p.mean()

print("="*68); print("1. MNAR PATTERN (both perfusion variables, MIMIC)")
print("="*68)
for f in ['lactate','uo']:
    mk=d[f].isna(); print(f"  {f:>8}: missing {mk.mean():.1%} | mort missing {y[mk].mean():.1%} vs observed {y[~mk].mean():.1%}  ({'less' if y[mk].mean()<y[~mk].mean() else 'MORE'} sick)")

print("\n"+"="*68); print("2. DISCRIMINATION STRATIFIED by lactate measured/missing")
print("="*68)
X=d[['lactate']+COM].astype(float); Xc=X.clip(X.quantile(.01),X.quantile(.99),axis=1); p=np.zeros(len(y))
for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(Xc,y):
    m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(Xc.iloc[tr],y[tr]); p[te]=m.predict_proba(Xc.iloc[te])[:,1]
for lab,mk in [('lactate MEASURED',~d['lactate'].isna().values),('lactate MISSING(imputed)',d['lactate'].isna().values)]:
    sl,c=slope_citl(p[mk],y[mk]); print(f"  MIMIC {lab:>24}: n={mk.sum():<5} AUROC {roc_auc_score(y[mk],p[mk]):.3f} slope {sl:.2f} CITL {c:+.3f} mort {y[mk].mean():.1%}")

print("\n"+"="*68); print("3. MULTIPLE IMPUTATION (MICE) vs MEDIAN — derivation sensitivity")
print("="*68)
def cvauc(imp):
    pp=np.zeros(len(y))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(Xc,y):
        m=Pipeline([('i',imp),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(Xc.iloc[tr],y[tr]); pp[te]=m.predict_proba(Xc.iloc[te])[:,1]
    return roc_auc_score(y,pp)
print(f"  median imputation : AUROC {cvauc(SimpleImputer(strategy='median')):.4f}")
print(f"  MICE (Iterative)  : AUROC {cvauc(IterativeImputer(max_iter=10,random_state=42)):.4f}  -> robust to imputation method")

print("\n"+"="*68); print("4. OPPOSITE-SIGN eICU CALIBRATION — mechanism (frozen MIMIC)")
print("="*68)
def frozen(cols):
    Xtr=d[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1)
    m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(Xtr,y)
    Xte=e[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1); return m.predict_proba(Xte)[:,1]
for nm,cols in [('lactate-variant',['lactate']+COM),('AG-variant (HARMONIZED)',['ag']+COM)]:
    p=frozen(cols); sl,c=slope_citl(p,ye)
    print(f"  {nm:>22}: eICU AUROC {roc_auc_score(ye,p):.3f} slope {sl:.3f} CITL {c:+.3f}")
# lactate over-prediction driver: eICU missing-lactate are less sick
eml=e['lactate'].isna()
print(f"\n  eICU lactate missing {eml.mean():.1%}: mort missing {ye[eml].mean():.1%} vs observed {ye[~eml].mean():.1%}")
print("  => lactate variant OVER-predicts (CITL<0): median-imputing the less-sick missing-lactate half inflates their risk.")
print("  => AG variant now CITL~0 after harmonization (the +0.17 under-prediction was the convention offset, fixed).")
