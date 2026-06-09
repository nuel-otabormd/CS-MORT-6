import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42)
mim=pd.read_csv('/tmp/mimic_variants.csv').rename(columns={'uo_rate_mlkghr':'uo'})
out=pd.read_csv('/tmp/outcomes.csv')[['stay_id','dead_30d']]; d=mim.merge(out,on='stay_id',how='left')
COMMON=['uo','ohca_arrest','age','bun','rdw','bilirubin']
cols=['lactate']+COMMON
X=d[cols].astype(float); X=X.clip(X.quantile(.01),X.quantile(.99),axis=1)
def cv_auc(yv):
    p=np.zeros(len(yv))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,yv):
        m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X.iloc[tr],yv[tr])
        p[te]=m.predict_proba(X.iloc[te])[:,1]
    return roc_auc_score(yv,p),p
yin=d['in_hospital_mortality'].astype(int).values; y30=d['dead_30d'].astype(int).values
print("="*60); print("SECONDARY OUTCOME — 30-DAY MORTALITY")
print("="*60)
print(f"  in-hospital mortality: {yin.mean():.1%}   30-day: {y30.mean():.1%}")
print(f"  of {y30.sum()} 30-day deaths, {(yin&y30).sum()} ({(yin&y30).sum()/y30.sum():.1%}) were in-hospital")
print(f"  post-discharge deaths within 30d: {(y30&~yin.astype(bool)).sum()} ({(y30&~yin.astype(bool)).sum()/len(y30):.1%} of cohort)")
ain,_=cv_auc(yin); a30,p30=cv_auc(y30)
print(f"\n  CS-MORT-7 continuous CV AUROC — in-hospital: {ain:.3f}   30-day: {a30:.3f}")
# integer score (in-hospital-derived points) applied to 30-day
RISKCUT={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99],'bilirubin':[-1,1.2,2,99]}
PROTCUT={'uo':[-1,0.5,1.0,99]}; BIN={'ohca_arrest'}; FEATS=['lactate','uo','ohca_arrest','age','bun','rdw','bilirubin']
def ordc(f):
    if f in BIN: return d[f].fillna(0).astype(int)
    if f in PROTCUT:
        o=pd.cut(d[f],bins=PROTCUT[f],labels=False); o=o.fillna(o.median()); return (o.max()-o).astype(int)
    o=pd.cut(d[f],bins=RISKCUT[f],labels=False); return o.fillna(o.median()).astype(int)
O=pd.DataFrame({f:ordc(f) for f in FEATS})
m=LogisticRegression(max_iter=800).fit(O,yin); B=np.median(np.abs(m.coef_[0]))
pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int); score=(O.values*pts).sum(1)
print(f"  CS-MORT-7 INTEGER (in-hosp points) AUROC — in-hospital: {roc_auc_score(yin,score):.3f}   30-day: {roc_auc_score(y30,score):.3f}")
# 30-day calibration of continuous model
def calm(p,yv):
    p=np.clip(p,1e-6,1-1e-6); lp=np.log(p/(1-p))
    sl=LogisticRegression(max_iter=500).fit(lp.reshape(-1,1),yv).coef_[0][0]
    return sl, np.mean((p-yv)**2)
sl,br=calm(p30,y30); print(f"  30-day calibration (CV preds): slope {sl:.2f}, Brier {br:.3f}, mean-pred {p30.mean():.3f} vs obs {y30.mean():.3f}")
# gradient by integer category on 30-day
band=np.asarray(pd.cut(LogisticRegression(max_iter=500).fit(score.reshape(-1,1),yin).predict_proba(score.reshape(-1,1))[:,1],bins=[-1,.2,.4,.6,2],labels=['Low','Mod','High','VHigh']))
print("  30-day mortality by CS-MORT-7 category:")
for c in ['Low','Mod','High','VHigh']:
    mk=band==c; print(f"    {c:>5}: n={mk.sum():<5} in-hosp {yin[mk].mean():.1%}  30-day {y30[mk].mean():.1%}")
