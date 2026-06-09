# CS-MORT-6 dynamic/trajectory value test (substantiates the "serial monitoring" claim)
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
np.random.seed(42)
h=pd.read_csv('outputs/tables/horizon_mr.csv').rename(columns={'uo_rate':'uo'})  # canonical: python/analysis/horizon_mr.sql
RISKCUT={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}
PROT={'uo':[-1,0.5,1.0,99]}; F6=['lactate','uo','ohca_arrest','age','bun','rdw']
def score_at(df):
    parts=[]
    for c in F6:
        if c=='ohca_arrest': parts.append(df[c].fillna(0).astype(int).values*3)
        elif c in PROT:
            o=pd.cut(df[c],bins=PROT[c],labels=False); o=o.fillna(o.median()); parts.append((o.max()-o).astype(int).values)
        else:
            o=pd.cut(df[c],bins=RISKCUT[c],labels=False); o=o.fillna(o.median()); parts.append(o.astype(int).values*(2 if c=='lactate' else 1))
    return np.sum(parts,axis=0)
h['score']=score_at(h)
w=h.pivot_table(index='stay_id',columns='horizon_h',values='score')
meta=h[h.horizon_h==24][['stay_id','in_hospital_mortality']].set_index('stay_id')
alive48=h[(h.horizon_h==48)&(h.alive_at_T==1)]['stay_id']
df=w.join(meta).loc[w.index.isin(alive48)].dropna(subset=[24,48]); y=df['in_hospital_mortality'].astype(int).values
df['delta']=df[48]-df[24]
def auc(cols): X=df[cols].values; return roc_auc_score(y,LogisticRegression(max_iter=500).fit(X,y).predict_proba(X)[:,1])
print(f"alive@48 n={len(df)} residual mort {y.mean():.1%}")
print(f"score@24 {auc([24]):.4f} | score@48 {auc([48]):.4f} | score@24+delta {auc([24,'delta']):.4f} (delta +{auc([24,'delta'])-auc([24]):.4f})")
df['traj']=pd.cut(df['delta'],bins=[-99,-1,1,99],labels=['Improved','Stable','Worsened'])
for t in ['Improved','Stable','Worsened']:
    mk=(df['traj']==t).values; print(f"  {t}: n={mk.sum()} mort {y[mk].mean():.1%}")
mid=df[(df[24]>=4)&(df[24]<=7)]; ym=mid['in_hospital_mortality'].astype(int).values
print("within score@24=4-7:")
for t in ['Improved','Stable','Worsened']:
    mk=(mid['traj']==t).values
    if mk.sum()>5: print(f"  {t}: n={mk.sum()} mort {ym[mk].mean():.1%}")
