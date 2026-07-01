"""
CS-MORT-6 — pipeline verification. Reproduces the published integer points, the
SCAI stage distribution, and the within-stage tertile cells (Figure 4) from the
canonical tables. Method mirrors python/analysis/scai_rebuild.py.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
np.random.seed(42)
DATA='data/'

# ---------- load MIMIC ----------
sc=pd.read_csv(DATA+'scai_components_mimic.csv')
f=pd.read_csv(DATA+'cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})
d=sc.merge(f[['stay_id','in_hospital_mortality','lactate','uo','age','bun','rdw',
              'aniongap_harmonized','ohca_arrest']].rename(columns={'ohca_arrest':'ohca_feat'}),
           on='stay_id',how='left')
y=d['in_hospital_mortality'].astype(int).values

# ---------- manuscript escalation-anchored SCAI staging (scai_new) ----------
sup=d['pressor_count']+d['inotrope_flag']; lac=d['lactate_max']; mcs=d['mcs_24h_count']
hypo=(d['sbp_min']<90)|(d['mbp_min']<65)
def stage(i):
    if d['ohca_arrest'].iloc[i]==1 or sup.iloc[i]>=3 or mcs.iloc[i]>=2: return 'E'
    if sup.iloc[i]==2 or mcs.iloc[i]>=1 or (lac.iloc[i]>4 and sup.iloc[i]>=1): return 'D'
    if sup.iloc[i]>=1 or (lac.iloc[i]>=2 and hypo.iloc[i]): return 'C'
    if hypo.iloc[i] or lac.iloc[i]>=2: return 'B'
    return 'A'
d['scai']=[stage(i) for i in range(len(d))]

# ---------- CS-MORT-6 integer score (Sullivan; points from |coef|/median) ----------
RISKCUT={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}
PROT={'uo':[-1,0.5,1.0,99]}; BIN={'ohca'}
def ordc(df,col):
    if col=='ohca': return df['ohca_feat'].fillna(0).astype(int)
    if col in PROT:
        o=pd.cut(df[col],bins=PROT[col],labels=False); o=o.fillna(o.median()); return (o.max()-o).astype(int)
    o=pd.cut(df[col],bins=RISKCUT[col],labels=False); return o.fillna(o.median()).astype(int)
def build_score(df,feats):
    O=pd.DataFrame({c:ordc(df,c) for c in feats})
    m=LogisticRegression(max_iter=800).fit(O,df['in_hospital_mortality'].astype(int))
    B=np.median(np.abs(m.coef_[0])); pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
    return (O.values*pts).sum(1), dict(zip(feats,pts))
F6=['lactate','uo','ohca','age','bun','rdw']
d['score'],pts6=build_score(d,F6)
print("Integer points (CS-MORT-6):",pts6,"  score range",int(d.score.min()),"-",int(d.score.max()))

print("\nSCAI stage distribution (manuscript expects A~8 B~464 C=1000 D=781 E=850):")
g=d.groupby('scai').agg(n=('stay_id','size'),mort=('in_hospital_mortality','mean'))
print(g.assign(mort=(g['mort']*100).round(1)).to_string())

# ---------- within-stage tertiles vs fig4_withinstage.csv ----------
print("\nWITHIN-STAGE tertiles (compare to fig4_withinstage.csv MIMIC rows):")
print(f"  {'stage':>5} {'tertile':>7} {'n':>5} {'mort%':>6}")
for s in ['B','C','D','E']:
    sub=d[d.scai==s]
    if len(sub)<30: continue
    t=pd.qcut(sub['score'],3,labels=False,duplicates='drop'); ys=sub['in_hospital_mortality'].values
    for k,lab in zip(range(int(t.max())+1),['Low','Mid','High']):
        print(f"  {s:>5} {lab:>7} {(t==k).sum():>5} {ys[t==k].mean()*100:>6.1f}")
