import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
np.random.seed(42)
# ---- integer scorers ----
RISKCUT={'lactate':[-1,2,4,99],'aniongap':[-1,12,18,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}
PROT={'uo':[-1,0.5,1.0,99]}
def integ(df, perf):  # perf = 'lactate' or 'aniongap'
    feats=[perf,'uo','ohca_arrest','age','bun','rdw']; parts=[]
    for c in feats:
        if c=='ohca_arrest': parts.append(df[c].fillna(0).astype(int).values*3)
        elif c in PROT:
            o=pd.cut(df[c],bins=PROT[c],labels=False); o=o.fillna(o.median()); parts.append((o.max()-o).astype(int).values)
        else:
            o=pd.cut(df[c],bins=RISKCUT[c],labels=False); o=o.fillna(o.median()); parts.append(o.astype(int).values*(2 if c==perf else 1))
    return np.sum(parts,axis=0)
def coarse_stage(arrest,mcs,support):  # E>D>C>B hierarchy on RELIABLE signals
    s=np.where(arrest==1,'E',np.where(mcs==1,'D',np.where(support==1,'C','B'))); return s
def withinstage(name, df, y, score):
    df=df.copy(); df['y']=y; df['score']=score
    print(f"\n  [{name}] n={len(df)}  overall mort {y.mean():.1%}")
    print(f"   {'stage':>5} {'n':>5} {'mort':>6} | {'T1':>6} {'T2':>6} {'T3':>6} {'spread':>7}")
    for s in ['B','C','D','E']:
        sub=df[df.stage==s]
        if len(sub)<25: continue
        t=pd.qcut(sub['score'],3,labels=False,duplicates='drop'); ys=sub['y'].values
        mr=[ys[t==k].mean() for k in range(int(t.max())+1)]
        print(f"   {s:>5} {len(sub):>5} {sub['y'].mean():>5.1%} | {mr[0]:>5.1%} {mr[1] if len(mr)>1 else float('nan'):>5.1%} {mr[-1]:>5.1%} {(mr[-1]-mr[0])*100:>6.1f}")
# ===== eICU =====
e=pd.read_csv('outputs/tables/cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})  # canonical: sql/07_eicu_canonical.sql
sc=pd.read_csv('outputs/tables/eicu_scai_components.csv').drop(columns=['mcs']); mc=pd.read_csv('outputs/tables/eicu_mcs.csv')  # canonical: sql/10_eicu_scai_components.sql
e=e.merge(sc,on='patientunitstayid',how='left').merge(mc,on='patientunitstayid',how='left')
e['mcs']=e['mcs'].fillna(0); e['support']=((e['vaso_count']>0)|(e['inotrope_flag']==1)).astype(int)
e['stage']=coarse_stage(e['arrest_dx'].fillna(0).values, e['mcs'].values, e['support'].values)
ye=e['hosp_mort'].astype(int).values
print("="*60); print("eICU staging dist:", {s:int((e.stage==s).sum()) for s in ['B','C','D','E']})
print("eICU stage mortality:", {s:round(ye[e.stage==s].mean(),3) for s in ['B','C','D','E'] if (e.stage==s).sum()})
withinstage("eICU AG-integer", e, ye, integ(e,'aniongap'))
# ===== MIMIC same coarse staging =====
m=pd.read_csv('outputs/tables/scai_components_mimic.csv').merge(pd.read_csv('outputs/tables/cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})[['stay_id','in_hospital_mortality','lactate','uo','age','bun','rdw']],on='stay_id',how='left')
m['support']=((m['pressor_count']>0)|(m['inotrope_flag']==1)).astype(int)
m['stage']=coarse_stage(m['ohca_arrest'].values, (m['mcs_24h_count']>0).astype(int).values, m['support'].values)
ym=m['in_hospital_mortality'].astype(int).values
print("\n"+"="*60); print("MIMIC staging dist:", {s:int((m.stage==s).sum()) for s in ['B','C','D','E']})
print("MIMIC stage mortality:", {s:round(ym[m.stage==s].mean(),3) for s in ['B','C','D','E'] if (m.stage==s).sum()})
withinstage("MIMIC lactate-integer (same coarse staging)", m, ym, integ(m,'lactate'))
