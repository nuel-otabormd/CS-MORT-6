# FULL RE-AUDIT: reproduce every headline number from persisted outputs/ (not /tmp),
# flag any inconsistency, verify integrity of the canonical CS-MORT-6 build.
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42); OK=[]; FLAG=[]
d=pd.read_csv('outputs/tables/cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
e=pd.read_csv('outputs/tables/cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
y=d['in_hospital_mortality'].astype(int).values; ye=e['hosp_mort'].astype(int).values
def chk(name,val,exp,tol=0.003):
    s='OK' if abs(val-exp)<=tol else 'FLAG'; (OK if s=='OK' else FLAG).append(f"{name}: {val:.4f} (exp {exp}) {s}"); print(f"  [{s}] {name}: {val:.4f} (expected ~{exp})")
# integrity
print("INTEGRITY:")
print(f"  MIMIC n={len(d)} (exp 3103), eICU n={len(e)} (exp 1866); MIMIC dup={d.stay_id.duplicated().sum()}, eICU dup={e.patientunitstayid.duplicated().sum()}")
print(f"  AG harmonized formula errors: {((d.ag-(d.sodium-(d.chloride+d.bicarbonate))).abs()>0.01).sum()}")
print(f"  mortality MIMIC {y.mean():.3f} (exp .383), eICU {ye.mean():.3f} (exp .345)")
COM=['uo','ohca_arrest','age','bun','rdw']
def cv(cols,yv=y):
    X=d[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1); p=np.zeros(len(yv))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,yv):
        m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X.iloc[tr],yv[tr]); p[te]=m.predict_proba(X.iloc[te])[:,1]
    return roc_auc_score(yv,p)
def frozen(cols):
    X=d[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1)
    m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X,y)
    Xe=e[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1); return roc_auc_score(ye,m.predict_proba(Xe)[:,1])
print("\nHEADLINE NUMBERS (reproduced from outputs/):")
chk("MIMIC continuous CV (lactate)",cv(['lactate']+COM),0.778)
chk("MIMIC continuous CV (AG)",cv(['ag']+COM),0.762)
chk("eICU frozen AG (harmonized)",frozen(['ag']+COM),0.748)
chk("eICU frozen lactate",frozen(['lactate']+COM),0.757)
chk("30-day continuous CV",cv(['lactate']+COM,d['dead_30d'].astype(int).values),0.783)
# integer
RC={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}; PR={'uo':[-1,0.5,1.0,99]}; F6=['lactate','uo','ohca_arrest','age','bun','rdw']
O=[]
for c in F6:
    if c=='ohca_arrest': O.append(d[c].fillna(0).astype(int).values)
    elif c in PR:
        o=pd.cut(d[c],bins=PR[c],labels=False); o=o.fillna(o.median()); O.append((o.max()-o).astype(int).values)
    else:
        o=pd.cut(d[c],bins=RC[c],labels=False); o=o.fillna(o.median()); O.append(o.astype(int).values)
O=np.column_stack(O); m=LogisticRegression(max_iter=800).fit(O,y); B=np.median(np.abs(m.coef_[0])); pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
print(f"\n  integer points {dict(zip(F6,pts))} (exp lactate2/ohca3/rest1)")
chk("integer AUROC",roc_auc_score(y,(O*pts).sum(1)),0.765)
print(f"\nAUDIT SUMMARY: {len(OK)} OK, {len(FLAG)} FLAGGED")
for f in FLAG: print("  !!",f)
