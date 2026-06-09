import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
np.random.seed(42)
def logit(p): p=np.clip(p,1e-6,1-1e-6); return np.log(p/(1-p))
def sig(x): return 1/(1+np.exp(-x))

class Frozen:
    def __init__(self,cols): self.cols=cols
    def fit(self,df,y):
        X=df[self.cols].astype(float).copy(); self.lo=X.quantile(.01); self.hi=X.quantile(.99)
        X=X.clip(self.lo,self.hi,axis=1); self.imp=SimpleImputer(strategy='median').fit(X)
        self.sc=StandardScaler().fit(self.imp.transform(X))
        self.lr=LogisticRegression(max_iter=800,C=0.5).fit(self.sc.transform(self.imp.transform(X)),y); return self
    def proba(self,df):
        X=df[self.cols].astype(float).copy().clip(self.lo,self.hi,axis=1)
        return self.lr.predict_proba(self.sc.transform(self.imp.transform(X)))[:,1]

mim=pd.read_csv('/tmp/mimic_variants.csv').rename(columns={'uo_rate_mlkghr':'uo'})
e=pd.read_csv('/tmp/eicu.csv').rename(columns={'uo_rate_mlkghr':'uo'}).merge(pd.read_csv('/tmp/eicu_cmp.csv'),on='patientunitstayid',how='left')
ye=e['hosp_mort'].astype(int).values; ym=mim['in_hospital_mortality'].astype(int).values
COMMON=['uo','ohca_arrest','age','bun','rdw','bilirubin']
e['p_ag']=Frozen(['aniongap']+COMMON).fit(mim,ym).proba(e)
RISK={0:0.005,1:0.014,2:0.039,3:0.10,4:0.235,5:0.46,6:0.702}
def bosma2(r):
    if any(pd.isna(r[c]) for c in ['bun_max','spo2_min','sbp_min','age','aniongap_max']): return np.nan
    return int(sum(bool(c) for c in [r['bun_max']>=25,r['spo2_min']<88,r['sbp_min']<80,r['mech_vent']==1,r['age']>=60,r['aniongap_max']>=14]))
e['bm']=e.apply(bosma2,axis=1); e['p_bm']=e['bm'].map(RISK)
b=e[e['bm'].notna()].copy(); yb=b['hosp_mort'].astype(int).values   # common scorable set for both
print(f"Common scorable set (BOS,MA2 complete): n={len(b)}, observed mortality {yb.mean():.1%}")

def ece_fixedbins(p,yv,edges):
    cat=np.digitize(p,edges[1:-1]); rows=[]; tot=0; N=len(yv)
    for i in range(len(edges)-1):
        mk=cat==i
        if mk.sum()==0: continue
        obs=yv[mk].mean(); pred=p[mk].mean(); n=mk.sum(); tot+=n*abs(obs-pred)
        rows.append((f"{edges[i]:.2f}-{edges[i+1]:.2f}",n,round(pred,3),round(obs,3),round(abs(obs-pred),3)))
    return tot/N, pd.DataFrame(rows,columns=['bin','n','pred','obs','|gap|'])

EDGES=[0,.10,.20,.30,.40,.60,1.01]   # identical bins for BOTH models
print("\n"+"="*64); print("VIEW 1 — AS-DEPLOYED (published/frozen risks, IDENTICAL fixed bins)")
print("="*64)
for nm,p in [('CS-MORT-7-AG (frozen MIMIC)',b['p_ag'].values),('BOS,MA2 (published RiskSLIM risks)',b['p_bm'].values)]:
    ec,tab=ece_fixedbins(p,yb,EDGES)
    citl=yb.mean()-p.mean()
    print(f"\n  {nm}:  ECE={ec:.3f}  CITL(obs-pred)={citl:+.3f}  meanPred={p.mean():.3f}")
    print(tab.to_string(index=False))

print("\n"+"="*64); print("VIEW 2 — RECALIBRATED to eICU (intercept+slope), residual ECE")
print("   isolates calibration SHAPE, removes baseline-rate transport penalty")
print("="*64)
for nm,p in [('CS-MORT-7-AG',b['p_ag'].values),('BOS,MA2',b['p_bm'].values)]:
    lr=LogisticRegression(max_iter=500).fit(logit(p).reshape(-1,1),yb)
    slope=lr.coef_[0][0]; inter=lr.intercept_[0]
    p_rc=lr.predict_proba(logit(p).reshape(-1,1))[:,1]
    ec,_=ece_fixedbins(p_rc,yb,EDGES)
    print(f"  {nm:14s}: slope={slope:.3f} intercept={inter:+.3f}  residual ECE={ec:.3f}")
