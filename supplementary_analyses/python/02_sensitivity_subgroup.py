"""
CS-MORT-6 — sensitivity and subgroup analyses. Outputs CSVs into out/ for the
supplementary figures. Verification in 01_verify_pipeline.py.
  - OHCA-free (CS-MORT-5) within-stage tertiles, MIMIC + eICU
  - anion-gap / BUN collinearity (correlation, VIF) + bootstrap reselection
  - subgroup (sex, race) AUROC + calibration slope + CITL with event counts
  - imputation sensitivity: multiple imputation (MICE) vs median (continuous model)
  - discrimination difference vs BOS,MA2 (point estimate + bootstrap 95% CI)
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
from scipy import stats
import os
np.random.seed(42)
DATA='data/'; OUT='out/'; os.makedirs(OUT,exist_ok=True)

# =========================================================================
# LOAD + build stages & scores (mirrors validated QC script)
# =========================================================================
sc=pd.read_csv(DATA+'scai_components_mimic.csv')
f=pd.read_csv(DATA+'cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})
demo=pd.read_csv(DATA+'mimic_demographics.csv')
m=sc.merge(f[['stay_id','in_hospital_mortality','lactate','uo','age','bun','rdw',
              'aniongap_harmonized','lactate_missing','uo_missing']],  # ohca_arrest already in sc
           on='stay_id',how='left').merge(demo,on='stay_id',how='left')
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

RISKCUT={'lactate':[-1,2,4,99],'aniongap':[-1,12,18,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}
PROT={'uo':[-1,0.5,1.0,99]}
def ordc(df,col,perf=None):
    if col=='ohca': return df['ohca_arrest'].fillna(0).astype(int)
    src = 'aniongap_harmonized' if col=='aniongap' else col
    if col in PROT:
        o=pd.cut(df[col],bins=PROT[col],labels=False); o=o.fillna(o.median()); return (o.max()-o).astype(int)
    o=pd.cut(df[src],bins=RISKCUT[col],labels=False); return o.fillna(o.median()).astype(int)
def build_score(df,feats,yv):
    O=pd.DataFrame({c:ordc(df,c) for c in feats})
    mdl=LogisticRegression(max_iter=800).fit(O,yv)
    B=np.median(np.abs(mdl.coef_[0])); pts=np.maximum(1,np.round(np.abs(mdl.coef_[0])/B)).astype(int)
    return (O.values*pts).sum(1), dict(zip(feats,pts))

F6=['lactate','uo','ohca','age','bun','rdw']
F5=['lactate','uo','age','bun','rdw']            # OHCA-free (CS-MORT-5)
m['score6'],_=build_score(m,F6,ym)
m['score5'],pts5=build_score(m,F5,ym)

# =========================================================================
# OHCA-FREE (CS-MORT-5) WITHIN-STAGE TERTILES
# =========================================================================
def within_rows(df,ycol,scorecol,cohort,stages=('B','C','D','E')):
    rows=[]
    for s in stages:
        sub=df[df.scai==s]
        if len(sub)<30: continue
        t=pd.qcut(sub[scorecol],3,labels=False,duplicates='drop'); ys=sub[ycol].astype(int).values
        labs=['Low','Mid','High']
        for k in range(int(t.max())+1):
            n=int((t==k).sum()); died=int(ys[t==k].sum()); mort=100*died/n
            lo,hi=stats.beta.ppf([.025,.975],died+0.5,n-died+0.5) if 0<died<n else (0,0)
            rows.append(dict(cohort=cohort,stage=s,tertile=labs[k],n=n,deaths=died,
                             mortality=round(mort,1),lo=round(lo*100,1),hi=round(hi*100,1)))
    return rows
r_mimic5=within_rows(m,'in_hospital_mortality','score5','MIMIC')

# eICU
e=pd.read_csv(DATA+'cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo'})
esc=pd.read_csv(DATA+'eicu_scai_components.csv')
e=e.merge(esc,on='patientunitstayid',how='left')
e['mcs']=e['mcs'].fillna(0); e['support']=((e['vaso_count']>0)|(e['inotrope_flag']==1)).astype(int)
e['scai']=np.where(e['arrest_dx'].fillna(0)==1,'E',np.where(e['mcs']==1,'D',np.where(e['support']==1,'C','B')))
ye=e['hosp_mort'].astype(int).values
# eICU integer scores (anion-gap formulation) with and without OHCA
def eicu_score(df,feats,yv):
    O=pd.DataFrame({c:ordc(df,c) for c in feats})
    mdl=LogisticRegression(max_iter=800).fit(O.fillna(O.median()),yv)
    B=np.median(np.abs(mdl.coef_[0])); pts=np.maximum(1,np.round(np.abs(mdl.coef_[0])/B)).astype(int)
    return (O.fillna(O.median()).values*pts).sum(1)
E6=['aniongap','uo','ohca','age','bun','rdw']; E5=['aniongap','uo','age','bun','rdw']
e['score6']=eicu_score(e,E6,ye); e['score5']=eicu_score(e,E5,ye)
r_eicu5=within_rows(e,'hosp_mort','score5','eICU')
pd.DataFrame(r_mimic5+r_eicu5).to_csv(OUT+'fig_s_ohca_free_withinstage.csv',index=False)
print("[within-stage] OHCA-free spreads (percentage points, High-Low):")
for coh,rows in [('MIMIC',r_mimic5),('eICU',r_eicu5)]:
    dd=pd.DataFrame(rows)
    for s in ['B','C','D','E']:
        ss=dd[dd.stage==s]
        if len(ss)>=2:
            sp=ss[ss.tertile=='High'].mortality.values[0]-ss[ss.tertile=='Low'].mortality.values[0]
            print(f"   {coh} stage {s}: Low {ss[ss.tertile=='Low'].mortality.values[0]:.1f}% -> High {ss[ss.tertile=='High'].mortality.values[0]:.1f}%  spread {sp:+.1f}")

# =========================================================================
# BUN / ANION-GAP COLLINEARITY + VIF + anion-gap-model betas
# =========================================================================
print("\n[collinearity] BUN / anion-gap:")
sub=m[['lactate','uo','ohca_arrest','age','bun','rdw','aniongap_harmonized']].dropna()
rp=stats.pearsonr(sub['bun'],sub['aniongap_harmonized'])
rs=stats.spearmanr(sub['bun'],sub['aniongap_harmonized'])
print(f"   Pearson r(BUN, anion gap) = {rp[0]:.3f} (p={rp[1]:.2e}); Spearman = {rs[0]:.3f}")
def vif(dfX,target):
    from sklearn.linear_model import LinearRegression
    others=[c for c in dfX.columns if c!=target]
    r2=LinearRegression().fit(dfX[others],dfX[target]).score(dfX[others],dfX[target])
    return 1/(1-r2)
Xlac=m[['lactate','uo','ohca_arrest','age','bun','rdw']].dropna()
Xag =m[['aniongap_harmonized','uo','ohca_arrest','age','bun','rdw']].dropna()
print(f"   VIF(BUN) in lactate model    = {vif(Xlac,'bun'):.2f}")
print(f"   VIF(BUN) in anion-gap model  = {vif(Xag,'bun'):.2f}")
print(f"   VIF(anion gap) in AG model   = {vif(Xag,'aniongap_harmonized'):.2f}")
# standardized betas (winsorized+standardized), both formulations -> confirm Table S4 (+0.259 vs +0.032)
def std_betas(df,perfcol):
    cols=[perfcol,'uo','ohca_arrest','age','bun','rdw']
    X=df[cols].astype(float).copy()
    for c in cols:
        if c=='ohca_arrest': continue
        lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    X=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X),columns=cols)
    Xs=X.copy()
    for c in cols:
        if c=='ohca_arrest': continue
        Xs[c]=(Xs[c]-Xs[c].mean())/Xs[c].std()
    b=LogisticRegression(max_iter=800,C=1e6).fit(Xs,df['in_hospital_mortality'].astype(int)).coef_[0]
    return dict(zip(cols,np.round(b,3)))
print("   Std betas lactate model :",std_betas(m,'lactate'))
print("   Std betas anion-gap model:",std_betas(m,'aniongap_harmonized'))
# bootstrap reselection frequency of each variable in the anion-gap model (LASSO stability)
from sklearn.linear_model import LogisticRegression as LR
cols_ag=['aniongap_harmonized','uo','ohca_arrest','age','bun','rdw']
Xag_full=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(m[cols_ag].astype(float)),columns=cols_ag)
Xag_full=(Xag_full-Xag_full.mean())/Xag_full.std()
sel=np.zeros(len(cols_ag)); B=500; rng=np.random.default_rng(42)
for _ in range(B):
    idx=rng.integers(0,len(ym),len(ym))
    l=LR(penalty='l1',solver='liblinear',C=0.1,max_iter=500).fit(Xag_full.iloc[idx],ym[idx])
    sel+=(np.abs(l.coef_[0])>1e-6)
print("   Anion-gap-model bootstrap reselection freq (C=0.1 L1, 500 resamples):",
      dict(zip(cols_ag,np.round(sel/B,3))))

# =========================================================================
# SUBGROUP PERFORMANCE: AUROC + slope + CITL with event counts
# =========================================================================
print("\n[subgroup] Performance (lactate model, 5-fold CV):")
COM=['uo','ohca_arrest','age','bun','rdw']
def slopecitl(p,yv):
    from scipy.optimize import minimize
    lp=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    sl=LogisticRegression(max_iter=500).fit(lp.reshape(-1,1),yv).coef_[0][0]
    citl=minimize(lambda a:-np.sum(yv*np.log(np.clip(1/(1+np.exp(-(a[0]+lp))),1e-9,1-1e-9))+
                  (1-yv)*np.log(np.clip(1-1/(1+np.exp(-(a[0]+lp))),1e-9,1-1e-9))),[0.0]).x[0]
    return sl,citl
Xf=m[['lactate']+COM].astype(float).clip(m[['lactate']+COM].quantile(.01),m[['lactate']+COM].quantile(.99),axis=1)
p=np.zeros(len(ym))
for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(Xf,ym):
    md=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(Xf.iloc[tr],ym[tr])
    p[te]=md.predict_proba(Xf.iloc[te])[:,1]
frows=[]
def auc_ci(yv,pv,Bt=2000):
    rng=np.random.default_rng(1); a=[]
    for _ in range(Bt):
        i=rng.integers(0,len(yv),len(yv))
        if len(np.unique(yv[i]))>1: a.append(roc_auc_score(yv[i],pv[i]))
    return np.percentile(a,[2.5,97.5])
for col,groups in [('gender',['M','F']),('race_group',['White','Black','Other/Unknown'])]:
    for glab in groups:
        mk=(m[col]==glab).values
        if mk.sum()<40: continue
        sl,c=slopecitl(p[mk],ym[mk]); au=roc_auc_score(ym[mk],p[mk]); lo,hi=auc_ci(ym[mk],p[mk])
        frows.append(dict(subgroup=glab,n=int(mk.sum()),deaths=int(ym[mk].sum()),
                          mortality=round(100*ym[mk].mean(),1),auroc=round(au,3),
                          auroc_lo=round(lo,3),auroc_hi=round(hi,3),slope=round(sl,2),citl=round(c,3)))
        print(f"   {glab:>14} n={mk.sum():>4} deaths={int(ym[mk].sum()):>4} mort={100*ym[mk].mean():>4.1f}% "
              f"AUROC={au:.3f} ({lo:.3f}-{hi:.3f}) slope={sl:.2f} CITL={c:+.3f}")
pd.DataFrame(frows).to_csv(OUT+'fairness_subgroups.csv',index=False)

# =========================================================================
# Imputation sensitivity: MICE vs median (continuous lactate model, 5-fold CV)
# =========================================================================
print("\n[imputation] MICE vs median (continuous model, 5-fold CV AUROC):")
def cv_auc(imp):
    Xc=m[['lactate']+COM].astype(float).clip(m[['lactate']+COM].quantile(.01),m[['lactate']+COM].quantile(.99),axis=1)
    pp=np.zeros(len(ym))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(Xc,ym):
        im=IterativeImputer(random_state=42,max_iter=10,sample_posterior=True) if imp=='mice' else SimpleImputer(strategy='median')
        md=Pipeline([('i',im),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(Xc.iloc[tr],ym[tr])
        pp[te]=md.predict_proba(Xc.iloc[te])[:,1]
    sl,c=slopecitl(pp,ym); return roc_auc_score(ym,pp),sl,c
for imp in ['median','mice']:
    a,sl,c=cv_auc(imp); print(f"   {imp:>7}: AUROC {a:.3f}  slope {sl:.2f}  CITL {c:+.3f}")

# =========================================================================
# Discrimination difference vs BOS,MA2 (commonly scorable eICU)
# =========================================================================
print("\n[comparator] CS-MORT-6 vs BOS,MA2 AUROC difference (commonly scorable eICU):")
# dca_eicu_cm6.csv is a patient-level export (cols: p_ag, bm, y). Place it in data/.
try:
    dca=pd.read_csv(DATA+'dca_eicu_cm6.csv')
    cc=dca.dropna(subset=['bm']).copy(); yv=cc['y'].astype(int).values
    a_cs=roc_auc_score(yv,cc['p_ag'].values); a_bm=roc_auc_score(yv,cc['bm'].values)
    rng=np.random.default_rng(42); diffs=[]
    for _ in range(2000):
        i=rng.integers(0,len(yv),len(yv))
        if len(np.unique(yv[i]))>1: diffs.append(roc_auc_score(yv[i],cc['p_ag'].values[i])-roc_auc_score(yv[i],cc['bm'].values[i]))
    lo,hi=np.percentile(diffs,[2.5,97.5])
    print(f"   n_commonly_scorable={len(yv)}  AUROC CS-MORT-6={a_cs:.3f}  BOS,MA2={a_bm:.3f}")
    print(f"   dAUROC = {a_cs-a_bm:+.3f}  (95% CI {lo:+.3f} to {hi:+.3f})")
except Exception as ex:
    print("   [dca file unavailable]",ex)
print("\nDONE. CSVs in out/:",os.listdir(OUT))
