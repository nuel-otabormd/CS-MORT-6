"""Within-stage resolution using ONLY the four variables not used in stage assignment
(age, urine output, BUN, RDW), with the published Table 2 integer weights (not refit).
Uses the study's SCAI staging (escalation-anchored for MIMIC, support-intensity
hierarchy for eICU) so cell counts are consistent with Figure 4.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from scipy import stats
np.random.seed(42)
D='data/'; OUT='out/'

# ---- MIMIC: rebuild manuscript staging (scai_new) ----
sc=pd.read_csv(D+'scai_components_mimic.csv')
f=pd.read_csv(D+'cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})
m=sc.merge(f[['stay_id','in_hospital_mortality','uo','age','bun','rdw']],on='stay_id',how='left')
ym=m['in_hospital_mortality'].astype(int).values
sup=m['pressor_count']+m['inotrope_flag']; lac=m['lactate_max']; mcs=m['mcs_24h_count']
hypo=(m['sbp_min']<90)|(m['mbp_min']<65)
def stage_m(i):
    if m['ohca_arrest'].iloc[i]==1 or sup.iloc[i]>=3 or mcs.iloc[i]>=2: return 'E'
    if sup.iloc[i]==2 or mcs.iloc[i]>=1 or (lac.iloc[i]>4 and sup.iloc[i]>=1): return 'D'
    if sup.iloc[i]>=1 or (lac.iloc[i]>=2 and hypo.iloc[i]): return 'C'
    if hypo.iloc[i] or lac.iloc[i]>=2: return 'B'
    return 'A'
m['scai']=[stage_m(i) for i in range(len(m))]

# ---- eICU: rebuild manuscript coarse staging ----
e=pd.read_csv(D+'cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})
esc=pd.read_csv(D+'eicu_scai_components.csv').drop(columns=['mcs'])   # use published (tight) MCS
mcp=pd.read_csv(D+'eicu_mcs_published.csv')                           # IABP/Impella/ECMO excl. removal (n=347)
e=e.merge(esc,on='patientunitstayid',how='left').merge(mcp,on='patientunitstayid',how='left')
e['mcs']=e['mcs'].fillna(0); e['support']=((e['vaso_count']>0)|(e['inotrope_flag']==1)).astype(int)
e['scai']=np.where(e['arrest_dx'].fillna(0)==1,'E',np.where(e['mcs']==1,'D',np.where(e['support']==1,'C','B')))
ye=e['hosp_mort'].astype(int).values

# ---- PUBLISHED Table 2 weights, four non-staging variables only (lactate=0, OHCA=0) ----
def subscore(df):
    age=pd.cut(df['age'],bins=[-1,65,80,999],labels=False)          # 0/1/2
    uo0=pd.cut(df['uo'],bins=[-1,0.5,1.0,99],labels=False); uo=(uo0.max()-uo0)  # protective ->0/1/2
    bun=pd.cut(df['bun'],bins=[-1,25,45,9e9],labels=False)          # 0/1/2
    rdw=pd.cut(df['rdw'],bins=[-1,14.5,16,99],labels=False)         # 0/1/2
    out=pd.DataFrame({'age':age,'uo':uo,'bun':bun,'rdw':rdw})
    return out.apply(lambda c:c.fillna(c.median())).sum(1)          # range 0-8
m['sub']=subscore(m); e['sub']=subscore(e)
print("Standalone AUROC of 4-variable non-staging sub-score (MIMIC):",round(roc_auc_score(ym,m['sub']),3))
print("Standalone AUROC (eICU):",round(roc_auc_score(ye,e['sub']),3))

def rows(df,ycol,cohort):
    r=[]
    for s in ['B','C','D','E']:
        sub=df[df.scai==s]
        if len(sub)<30: continue
        t=pd.qcut(sub['sub'],3,labels=False,duplicates='drop'); ys=sub[ycol].astype(int).values
        labs=['Low','Mid','High']
        for k in range(int(t.max())+1):
            n=int((t==k).sum()); dd=int(ys[t==k].sum()); mo=100*dd/n
            lo,hi=stats.beta.ppf([.025,.975],dd+0.5,n-dd+0.5)
            r.append(dict(cohort=cohort,stage=s,tertile=labs[k],n=n,deaths=dd,
                          mortality=round(mo,1),lo=round(lo*100,1),hi=round(hi*100,1)))
    return r
allrows=rows(m,'in_hospital_mortality','MIMIC-IV')+rows(e,'hosp_mort','eICU')
out=pd.DataFrame(allrows); out.to_csv(OUT+'fig_s3_nonstaging_withinstage.csv',index=False)
print("\nStage totals (must match Figure 4):")
for coh in ['MIMIC-IV','eICU']:
    print(" ",coh,dict(out[out.cohort==coh].groupby('stage')['n'].sum()))
print("\nHigh-Low spreads (percentage points):")
for coh in ['MIMIC-IV','eICU']:
    for s in ['B','C','D','E']:
        ss=out[(out.cohort==coh)&(out.stage==s)]
        if len(ss)>=2:
            lo=ss[ss.tertile=='Low'].mortality.values[0]; hi=ss[ss.tertile=='High'].mortality.values[0]
            print(f"   {coh} {s}: {lo:.1f} -> {hi:.1f}  ({hi-lo:+.1f})")
