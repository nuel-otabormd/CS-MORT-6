import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('outputs/tables/scai_components_mimic.csv')  # canonical: sql/09_scai_components.sql (projection of cs_features_baseline)
f=pd.read_csv('outputs/tables/cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})[['stay_id','in_hospital_mortality','lactate','uo','age','bun','rdw']]
d=d.merge(f,on='stay_id',how='left'); y=d['in_hospital_mortality'].astype(int).values
sup=d['pressor_count']+d['inotrope_flag']; lac=d['lactate_max']; mcs=d['mcs_24h_count']
hypo=(d['sbp_min']<90)|(d['mbp_min']<65)
def stage(i):
    if d['ohca_arrest'].iloc[i]==1 or sup.iloc[i]>=3 or mcs.iloc[i]>=2: return 'E'
    if sup.iloc[i]==2 or mcs.iloc[i]>=1 or (lac.iloc[i]>4 and sup.iloc[i]>=1): return 'D'
    if sup.iloc[i]>=1 or (lac.iloc[i]>=2 and hypo.iloc[i]): return 'C'
    if hypo.iloc[i] or lac.iloc[i]>=2: return 'B'
    return 'A'
d['scai_new']=[stage(i) for i in range(len(d))]
# CS-MORT-6 integer score
RISKCUT={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}
PROT={'uo':[-1,0.5,1.0,99]}; BIN={'ohca_arrest'}; F6=['lactate','uo','ohca_arrest','age','bun','rdw']
def ordc(col):
    if col in BIN: return d[col].fillna(0).astype(int)
    if col in PROT:
        o=pd.cut(d[col],bins=PROT[col],labels=False); o=o.fillna(o.median()); return (o.max()-o).astype(int)
    o=pd.cut(d[col],bins=RISKCUT[col],labels=False); return o.fillna(o.median()).astype(int)
O=pd.DataFrame({c:ordc(c) for c in F6}); m=LogisticRegression(max_iter=800).fit(O,y)
B=np.median(np.abs(m.coef_[0])); pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int); d['score']=(O.values*pts).sum(1)
NUM={'A':0,'B':1,'C':2,'D':3,'E':4}
print("="*64); print("SCAI-CSWG REBUILD (drug/device/arrest hierarchy, not BP-nadir)")
print("="*64)
for col,lab in [('scai_old','OLD (24h-min-BP, over-assigns E)'),('scai_new','NEW (escalation-anchored)')]:
    g=d.groupby(col).agg(n=('stay_id','size'),mort=('in_hospital_mortality','mean'))
    dist=" ".join(f"{s}:{int(g.loc[s,'n']) if s in g.index else 0}({g.loc[s,'mort']:.0%})" for s in ['A','B','C','D','E'] if s in g.index)
    au=roc_auc_score(y,d[col].map(NUM))
    print(f"  {lab}\n     dist {dist}   ordinal AUROC {au:.3f}")
print(f"  CS-MORT-6 integer AUROC: {roc_auc_score(y,d['score']):.3f}")
print("\nWITHIN-STAGE RESOLUTION (NEW staging) — CS-MORT-6 tertiles per stage:")
print(f"  {'stage':>5} {'n':>5} {'stage mort':>10} | {'T1':>6} {'T2':>6} {'T3':>6} {'spread':>7} {'within-AUROC':>12}")
for s in ['B','C','D','E']:
    sub=d[d['scai_new']==s]
    if len(sub)<30: continue
    t=pd.qcut(sub['score'],3,labels=False,duplicates='drop'); ys=sub['in_hospital_mortality'].values
    mr=[ys[t==k].mean() for k in range(3)]
    wa=roc_auc_score(ys,sub['score']) if len(np.unique(ys))>1 else float('nan')
    print(f"  {s:>5} {len(sub):>5} {sub['in_hospital_mortality'].mean():>9.1%} | {mr[0]:>5.1%} {mr[1]:>5.1%} {mr[2]:>5.1%} {(mr[2]-mr[0])*100:>6.1f} {wa:>11.3f}")
# nested: does stage add on top of CS-MORT-6?
from scipy import stats
import numpy as np
def lr_auc(cols): 
    X=d[cols].values; return roc_auc_score(y,LogisticRegression(max_iter=500).fit(X,y).predict_proba(X)[:,1])
a_score=lr_auc(['score']); a_both=lr_auc(['score']) if True else None
d['stage_num']=d['scai_new'].map(NUM)
a_s=lr_auc(['score']); a_sb=lr_auc(['score','stage_num']); a_stage=lr_auc(['stage_num'])
print(f"\n  Nested models: stage-alone {a_stage:.3f} | score-alone {a_s:.3f} | score+stage {a_sb:.3f} (stage adds {a_sb-a_s:+.3f})")
