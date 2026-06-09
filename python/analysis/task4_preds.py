import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
np.random.seed(42)
COMMON=['uo','ohca_arrest','age','bun','rdw','bilirubin']
def pipe(): return Pipeline([('imp',SimpleImputer(strategy='median')),('sc',StandardScaler()),('lr',LogisticRegression(max_iter=800,C=0.5))])
def clip99(df,cols,ref=None):
    X=df[cols].astype(float).copy()
    lo=(ref if ref is not None else X).quantile(.01); hi=(ref if ref is not None else X).quantile(.99)
    return X.clip(lo,hi,axis=1),lo,hi

mim=pd.read_csv('/tmp/mimic_variants.csv').rename(columns={'uo_rate_mlkghr':'uo'})
ym=mim['in_hospital_mortality'].astype(int).values
# ---- MIMIC internal: 5-fold CV predicted prob (lactate continuous model) ----
cols=['lactate']+COMMON; X,_,_=clip99(mim,cols)
cvp=np.zeros(len(ym))
for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,ym):
    m=pipe().fit(X.iloc[tr],ym[tr]); cvp[te]=m.predict_proba(X.iloc[te])[:,1]
pd.DataFrame({'p':cvp,'y':ym}).to_csv('/tmp/cal_mimic.csv',index=False)
print(f"MIMIC internal CV preds: n={len(ym)} mort={ym.mean():.3f} meanpred={cvp.mean():.3f}")

# ---- eICU external: frozen full-MIMIC models ----
e=pd.read_csv('/tmp/eicu.csv').rename(columns={'uo_rate_mlkghr':'uo'}).merge(pd.read_csv('/tmp/eicu_cmp.csv'),on='patientunitstayid',how='left')
ye=e['hosp_mort'].astype(int).values
def frozen(cols):
    Xtr,lo,hi=clip99(mim,cols); m=pipe().fit(Xtr,ym)
    Xte=e[cols].astype(float).clip(lo,hi,axis=1); return m.predict_proba(Xte)[:,1]
e['p_lac']=frozen(['lactate']+COMMON); e['p_ag']=frozen(['aniongap']+COMMON)
RISK={0:0.005,1:0.014,2:0.039,3:0.10,4:0.235,5:0.46,6:0.702}
def bosma2(r):
    if any(pd.isna(r[c]) for c in ['bun_max','spo2_min','sbp_min','age','aniongap_max']): return np.nan
    return int(sum(bool(c) for c in [r['bun_max']>=25,r['spo2_min']<88,r['sbp_min']<80,r['mech_vent']==1,r['age']>=60,r['aniongap_max']>=14]))
e['p_bm']=e.apply(bosma2,axis=1).map(RISK)
e[['p_lac','p_ag','p_bm']].assign(y=ye).to_csv('/tmp/cal_eicu.csv',index=False)
print(f"eICU external preds: n={len(ye)} mort={ye.mean():.3f} p_ag mean={e['p_ag'].mean():.3f} bosma scorable={e['p_bm'].notna().mean():.3f}")
