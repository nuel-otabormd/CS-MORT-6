# TRIPOD+AI items 14/23a/25 (fairness/subgroup) + 12d/23b (cluster heterogeneity)
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('outputs/tables/cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})
demo=pd.read_csv('outputs/tables/mimic_demographics.csv'); d=d.merge(demo,on='stay_id',how='left')  # canonical: sql/08_mimic_demographics.sql
y=d['in_hospital_mortality'].astype(int).values; COM=['uo','ohca_arrest','age','bun','rdw']
def slopecitl(p,yv):
    # CITL = formal calibration-in-the-large (logistic intercept with linear predictor as offset), NOT mean(y)-mean(p)
    from scipy.optimize import minimize
    lp=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    sl=LogisticRegression(max_iter=500).fit(lp.reshape(-1,1),yv).coef_[0][0]
    citl=minimize(lambda a:-np.sum(yv*np.log(np.clip(1/(1+np.exp(-(a[0]+lp))),1e-9,1-1e-9))+(1-yv)*np.log(np.clip(1-1/(1+np.exp(-(a[0]+lp))),1e-9,1-1e-9))),[0.0]).x[0]
    return sl, citl
X=d[['lactate']+COM].astype(float).clip(d[['lactate']+COM].quantile(.01),d[['lactate']+COM].quantile(.99),axis=1); p=np.zeros(len(y))
for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,y):
    m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X.iloc[tr],y[tr]); p[te]=m.predict_proba(X.iloc[te])[:,1]
print("="*64); print("FAIRNESS / SUBGROUP PERFORMANCE (TRIPOD+AI item 14/23a/25)")
print("="*64)
print(f"  {'subgroup':>16} {'n':>5} {'mort':>6} {'AUROC':>6} {'slope':>6} {'CITL':>7}")
for col,groups in [('gender',['M','F']),('race_group',['White','Black','Other/Unknown'])]:
    for g in groups:
        mk=(d[col]==g).values
        if mk.sum()<40: continue
        sl,c=slopecitl(p[mk],y[mk])
        print(f"  {g:>16} {mk.sum():>5} {y[mk].mean():>5.1%} {roc_auc_score(y[mk],p[mk]):>6.3f} {sl:>6.2f} {c:>+7.3f}")
print("  => report whether discrimination/calibration are equitable across sex and race.")

print("\n"+"="*64); print("CLUSTER HETEROGENEITY across eICU hospitals (TRIPOD+AI item 12d/23b)")
print("="*64)
mim=pd.read_csv('outputs/tables/cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'}); ym=mim['in_hospital_mortality'].astype(int).values
e=pd.read_csv('outputs/tables/cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
# canonical: SELECT patientunitstayid, hospitalid FROM physionet-data.eicu_crd.patient (CS cohort)
hosp=pd.read_csv('outputs/tables/eicu_hospital.csv').drop_duplicates('patientunitstayid'); e=e.merge(hosp,on='patientunitstayid',how='left'); ye=e['hosp_mort'].astype(int).values
Xtr=mim[['ag']+COM].astype(float).clip(mim[['ag']+COM].quantile(.01),mim[['ag']+COM].quantile(.99),axis=1)
mdl=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(Xtr,ym)
e['p']=mdl.predict_proba(e[['ag']+COM].astype(float).clip(mim[['ag']+COM].quantile(.01),mim[['ag']+COM].quantile(.99),axis=1))[:,1]
aucs=[]
for h,sub in e.groupby('hospitalid'):
    yy=sub['hosp_mort'].astype(int).values
    if len(sub)>=25 and 0<yy.sum()<len(yy): aucs.append(roc_auc_score(yy,sub['p']))
aucs=np.array(aucs)
print(f"  hospitals total {e.hospitalid.nunique()}, with >=25 scorable CS patients: {len(aucs)}")
print(f"  per-hospital AUROC: median {np.median(aucs):.3f}, IQR {np.percentile(aucs,25):.3f}-{np.percentile(aucs,75):.3f}, range {aucs.min():.3f}-{aucs.max():.3f}")
print(f"  pooled eICU AUROC {roc_auc_score(ye,e['p']):.3f} => wide range reflects small per-hospital samples (>=25 pts); per-site CIs wide.")
