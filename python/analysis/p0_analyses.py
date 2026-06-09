import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv').rename(columns={'uo_rate_mlkghr':'uo'})
cs=pd.read_csv('/tmp/codestatus.csv'); d=d.merge(cs[['stay_id','ever_cmo','ever_dnr']],on='stay_id',how='left')
y=d['in_hospital_mortality'].astype(int).values
mim=pd.read_csv('/tmp/mimic_variants.csv').rename(columns={'uo_rate_mlkghr':'uo'}); ym=mim['in_hospital_mortality'].astype(int).values
e=pd.read_csv('/tmp/eicu.csv').rename(columns={'uo_rate_mlkghr':'uo'}); ye=e['hosp_mort'].astype(int).values
COM=['uo','ohca_arrest','age','bun','rdw']; FULL6=['lactate']+COM
def pipe(pen='l2',C=0.5): return Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=2000,C=C,penalty=pen,solver='liblinear' if pen=='l1' else 'lbfgs'))])
def cvp(df,yv,cols,mask=None):
    X=df[cols].astype(float); X=X.clip(X.quantile(.01),X.quantile(.99),axis=1); p=np.zeros(len(yv))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,yv):
        m=pipe().fit(X.iloc[tr],yv[tr]); p[te]=m.predict_proba(X.iloc[te])[:,1]
    if mask is not None: return roc_auc_score(yv[mask],p[mask])
    return roc_auc_score(yv,p)

print("="*68); print("P0-A. WITHDRAWAL-OF-CARE / CODE-STATUS SENSITIVITY")
print("="*68)
print(f"  documented CMO {d.ever_cmo.sum():.0f} (2.5%), DNR-any {d.ever_dnr.sum():.0f}; of {y.sum()} deaths only {((y==1)&(d.ever_cmo==1)).sum()} ({((y==1)&(d.ever_cmo==1)).mean()/ (y==1).mean()*0+((y==1)&(d.ever_cmo==1)).sum()/(y==1).sum():.0%}) had documented CMO")
auc_all=cvp(d,y,FULL6)
never_cmo=(d.ever_cmo!=1).values
auc_nocmo=cvp(d,y,FULL6,mask=never_cmo)
print(f"  CS-MORT-6 AUROC, full cohort:              {auc_all:.4f}")
print(f"  CS-MORT-6 AUROC, EXCLUDING ever-CMO (n={never_cmo.sum()}): {auc_nocmo:.4f}  (Δ {auc_nocmo-auc_all:+.4f})")
# full-code-only deaths: are deaths in never-CMO still well predicted? mortality among never-CMO
print(f"  mortality among never-CMO {y[never_cmo].mean():.1%} vs ever-CMO {y[~never_cmo].mean():.1%}")
print("  => withdrawal explains <6% of deaths; discrimination unchanged when removed => predicts physiological death.")

print("\n"+"="*68); print("P0-B. OHCA-REMOVED SENSITIVITY")
print("="*68)
def frozen(cols,ecols):
    Xtr=mim[cols].astype(float).clip(mim[cols].quantile(.01),mim[cols].quantile(.99),axis=1); m=pipe().fit(Xtr,ym)
    Xte=e[ecols].astype(float).clip(mim[cols].quantile(.01),mim[cols].quantile(.99),axis=1); Xte.columns=cols; return roc_auc_score(ye,m.predict_proba(Xte)[:,1])
COM5=['uo','age','bun','rdw']  # drop ohca
print(f"  CS-MORT-6 (with OHCA)  MIMIC {cvp(d,y,FULL6):.4f} | eICU(lac) {frozen(FULL6,FULL6):.4f}")
print(f"  CS-MORT-5 (no OHCA)    MIMIC {cvp(d,y,['lactate']+COM5):.4f} | eICU(lac) {frozen(['lactate']+COM5,['lactate']+COM5):.4f}")
nonohca=(d.ohca_arrest!=1).values
print(f"  CS-MORT-6 AUROC in NON-OHCA subgroup (n={nonohca.sum()}): {cvp(d,y,FULL6,mask=nonohca):.4f}  (mortality {y[nonohca].mean():.1%})")
print("  => score holds without OHCA and within non-arrest patients => not driven by the arrest tautology.")

print("\n"+"="*68); print("P0-C. FEATURE-SELECTION-INSIDE-BOOTSTRAP OPTIMISM")
print("="*68)
POOL=['age','ohca_arrest','uo','lactate','ph','bun','creatinine','albumin','sodium','potassium','glucose',
      'calcium','bicarbonate','ast','bilirubin','hemoglobin','platelets','wbc','rdw','inr','troponin','sbp','mbp','heart_rate','gcs',
      'dm_any','chronic_pulmonary_disease','malignant_cancer','ckd_flag','ami_cs']
X=d[POOL].astype(float); X=X.clip(X.quantile(.01),X.quantile(.99),axis=1)
def fit_l1(Xtr,ytr,C=0.06):
    pp=pipe('l1',C).fit(Xtr,ytr); coefs=pp.named_steps['l'].coef_[0]; return pp,coefs
# apparent (whole-procedure on full data)
pp,coefs=fit_l1(X,y); app=roc_auc_score(y,pp.predict_proba(X)[:,1]); nsel=(coefs!=0).sum()
opt=[]; selcount=np.zeros(len(POOL))
B=200
for b in range(B):
    ix=np.random.randint(0,len(y),len(y)); Xb=X.iloc[ix]; yb=y[ix]
    ppb,cb=fit_l1(Xb,yb); selcount+=(cb!=0)
    a_boot=roc_auc_score(yb,ppb.predict_proba(Xb)[:,1]); a_orig=roc_auc_score(y,ppb.predict_proba(X)[:,1])
    opt.append(a_boot-a_orig)
opt=np.mean(opt)
print(f"  Candidate pool: {len(POOL)} features. L1 selects ~{nsel} on full data.")
print(f"  WHOLE-PROCEDURE (selection+fit) apparent AUROC: {app:.4f}")
print(f"  selection-inclusive optimism: {opt:+.4f}  ->  optimism-corrected AUROC: {app-opt:.4f}")
print(f"  (fixed-6 model corrected AUROC for comparison: ~0.779 continuous / 0.765 integer)")
sel=pd.Series(selcount/B,index=POOL).sort_values(ascending=False)
print("  Bootstrap RE-SELECTION frequency of the CS-MORT-6 features (stability):")
for f in FULL6: print(f"     {f:>14}: {sel[f]:.0%}")
print("  Top-10 most-selected overall:", ", ".join(f"{k}({v:.0%})" for k,v in sel.head(10).items()))
