import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42)
# ---------- data ----------
# canonical committed sources (harmonized anion gap for both cohorts, per sql/06 and sql/07)
d=pd.read_csv('outputs/tables/cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'aniongap'})
y=d['in_hospital_mortality'].astype(int).values; y30=d['dead_30d'].astype(int).values
mim=d; ym=y  # frozen model trains on the canonical MIMIC table
e=pd.read_csv('outputs/tables/cs_eicu_canonical.csv').drop(columns=['aniongap']).rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'aniongap'}); ye=e['hosp_mort'].astype(int).values
F6=['lactate','uo','ohca_arrest','age','bun','rdw']; COM=['uo','ohca_arrest','age','bun','rdw']
def pipe(): return Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))])
def clipd(df,cols,ref=None): 
    r=ref if ref is not None else df; return df[cols].astype(float).clip(r[cols].quantile(.01),r[cols].quantile(.99),axis=1)
def cv(df,yv,cols):
    X=clipd(df,cols); p=np.zeros(len(yv))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,yv):
        m=pipe().fit(X.iloc[tr],yv[tr]); p[te]=m.predict_proba(X.iloc[te])[:,1]
    return p
print("="*66); print("CS-MORT-6 FINAL — lactate, UO, OHCA, age, BUN, RDW"); print("="*66)
pin=cv(d,y,['lactate']+COM); print(f"  MIMIC continuous CV AUROC (in-hosp): {roc_auc_score(y,pin):.4f}")
p30=cv(d,y30,['lactate']+COM);  print(f"  MIMIC continuous CV AUROC (30-day):  {roc_auc_score(y30,p30):.4f}")
pd.DataFrame({'p':pin,'y':y}).to_csv('outputs/tables/cal_mimic6.csv',index=False)
# ---------- integer score ----------
RISKCUT={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}
PROT={'uo':[-1,0.5,1.0,99]}; BIN={'ohca_arrest'}
def ordframe(df):
    cols={}
    for f in F6:
        if f in BIN: cols[f]=df[f].fillna(0).astype(int).values
        elif f in PROT:
            o=pd.cut(df[f],bins=PROT[f],labels=False); o=o.fillna(o.median()); cols[f]=(o.max()-o).astype(int).values
        else:
            o=pd.cut(df[f],bins=RISKCUT[f],labels=False); cols[f]=o.fillna(o.median()).astype(int).values
    return np.column_stack([cols[f] for f in F6])
def fitpts(O,yy): m=LogisticRegression(max_iter=800).fit(O,yy); B=np.median(np.abs(m.coef_[0])); return np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
O=ordframe(d); pts=fitpts(O,y); score=(O*pts).sum(1)
print(f"\n  INTEGER points: {dict(zip(F6,pts))}  range {score.min()}-{score.max()}")
print(f"  INTEGER AUROC (in-sample): {roc_auc_score(y,score):.4f}")
# bootstrap optimism (re-derive points each boot)
opt=[]
for b in range(500):
    ix=np.random.randint(0,len(y),len(y)); pb=fitpts(O[ix],y[ix])
    opt.append(roc_auc_score(y[ix],(O[ix]*pb).sum(1))-roc_auc_score(y,(O*pb).sum(1)))
print(f"  INTEGER optimism-corrected AUROC: {roc_auc_score(y,score)-np.mean(opt):.4f} (optimism {np.mean(opt):+.4f})")
# categories with VeryLow rule-out tier (predicted-risk bands <10/20/40/60)
risk=LogisticRegression(max_iter=500).fit(score.reshape(-1,1),y).predict_proba(score.reshape(-1,1))[:,1]
band=np.asarray(pd.cut(risk,bins=[-1,.10,.20,.40,.60,2],labels=['VeryLow','Low','Mod','High','VHigh']))
print("\n  RISK CATEGORIES (bands <10/20/40/60% predicted; non-arbitrary):")
prev=-1; mono=True
for c in ['VeryLow','Low','Mod','High','VHigh']:
    mk=band==c
    if not mk.sum(): continue
    mr=y[mk].mean(); mono=mono and mr>=prev; prev=mr
    print(f"    {c:>8}: score {int(score[mk].min()):>2}-{int(score[mk].max()):<2} n={mk.sum():<5} mort {mr:.1%}")
print(f"    MONOTONIC: {mono}")
# diagnostic accuracy at key thresholds
print("\n  DIAGNOSTIC ACCURACY (death if score>=t):")
P=y.sum(); Ng=len(y)-P
print(f"   {'t':>2} {'sens':>5} {'spec':>5} {'PPV':>5} {'NPV':>5} {'LR+':>5}")
for t in [3,6,8,9]:
    pr=score>=t; tp=(pr&(y==1)).sum(); fp=(pr&(y==0)).sum(); fn=(~pr&(y==1)).sum(); tn=(~pr&(y==0)).sum()
    print(f"   {t:>2} {tp/P:>5.2f} {tn/Ng:>5.2f} {tp/max(tp+fp,1):>5.2f} {tn/max(tn+fn,1):>5.2f} {(tp/P)/max(1-tn/Ng,1e-9):>5.2f}")
# ---------- eICU external (frozen MIMIC) ----------
def frozen(cols): return pipe().fit(clipd(mim,cols),ym).predict_proba(clipd(e,cols,ref=mim))[:,1]
e['p_ag']=frozen(['aniongap']+COM); e['p_lac']=frozen(['lactate']+COM)
e[['p_ag','p_lac']].assign(y=ye).to_csv('outputs/tables/cal_eicu6.csv',index=False)
print(f"\n  eICU external AUROC: AG-6 {roc_auc_score(ye,e['p_ag']):.4f} | lactate-6 {roc_auc_score(ye,e['p_lac']):.4f}")
# eICU integer gradient (AG-variant deployable)
RC_AG={**{k:v for k,v in RISKCUT.items() if k!='lactate'},'aniongap':[-1,12,18,99]}
FAG=['aniongap','uo','ohca_arrest','age','bun','rdw']
def ord_ag(df):
    cols={}
    for f in FAG:
        if f in BIN: cols[f]=df[f].fillna(0).astype(int).values
        elif f in PROT:
            o=pd.cut(df[f],bins=PROT[f],labels=False); o=o.fillna(o.median()); cols[f]=(o.max()-o).astype(int).values
        else:
            o=pd.cut(df[f],bins=RC_AG[f],labels=False); cols[f]=o.fillna(o.median()).astype(int).values
    return np.column_stack([cols[f] for f in FAG])
Oag=ord_ag(mim); pag=fitpts(Oag,ym); sag=(ord_ag(e)*pag).sum(1)
qs=np.quantile(sag,[1/3,2/3]); cat=np.digitize(sag,qs)
print("  eICU AG-integer gradient (deployable):", " ".join(f"{['Low','Mid','High'][i]} {ye[cat==i].mean():.1%}" for i in range(3)))
