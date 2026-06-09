# CANONICAL CS-MORT-6 RESULTS GENERATOR — reads ONLY canonical persisted tables,
# regenerates every table on CS-MORT-6 (harmonized AG), saves to outputs/tables/.
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42)
OUT='outputs/tables/'
d=pd.read_csv(OUT+'cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'}); y=d['in_hospital_mortality'].astype(int).values
e=pd.read_csv(OUT+'cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'}); ye=e['hosp_mort'].astype(int).values
cmp=pd.read_csv(OUT+'cs_eicu_comparators.csv')  # canonical source: sql/05_eicu_comparators.sql
COM=['uo','ohca_arrest','age','bun','rdw']
def auc_ci(yv,p,B=2000):
    rng=np.random.default_rng(42); a=[]
    for _ in range(B):
        i=rng.integers(0,len(yv),len(yv))
        if yv[i].sum() in (0,len(i)): continue
        a.append(roc_auc_score(yv[i],p[i]))
    return np.percentile(a,2.5),np.percentile(a,97.5)
def slope_citl_brier(p,yv):
    # CITL = formal calibration-in-the-large: intercept of a logistic model with the
    # linear predictor as a fixed offset (slope=1), per Steyerberg/Van Calster. NOT mean(y)-mean(p).
    from scipy.optimize import minimize
    lp=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    sl=LogisticRegression(max_iter=500).fit(lp.reshape(-1,1),yv).coef_[0][0]
    def nll(a):
        pr=np.clip(1/(1+np.exp(-(a[0]+lp))),1e-9,1-1e-9)
        return -np.sum(yv*np.log(pr)+(1-yv)*np.log(1-pr))
    citl=minimize(nll,[0.0]).x[0]
    return round(sl,3), round(citl,3), round(np.mean((p-yv)**2),3)
def cv_pred(cols):
    X=d[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1); p=np.zeros(len(y))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,y):
        m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X.iloc[tr],y[tr]); p[te]=m.predict_proba(X.iloc[te])[:,1]
    return p
def frozen(cols):
    X=d[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1)
    m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X,y)
    Xe=e[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1); return m.predict_proba(Xe)[:,1]

# ---- TABLE 3: discrimination + calibration (CS-MORT-6 variants) ----
rows=[]
for nm,perf in [('CS-MORT-6 (lactate)','lactate'),('CS-MORT-6-AG (harmonized, deployable)','ag')]:
    cols=[perf]+COM; pcv=cv_pred(cols); pe=frozen(cols)
    lo,hi=auc_ci(ye,pe); sl,c,br=slope_citl_brier(pe,ye)
    rows.append({'model':nm,'MIMIC_CV_AUROC':round(roc_auc_score(y,pcv),3),'eICU_AUROC':round(roc_auc_score(ye,pe),3),
                 'eICU_CI':f"{lo:.3f}-{hi:.3f}",'eICU_slope':sl,'eICU_CITL':c,'eICU_Brier':br})
t3=pd.DataFrame(rows); t3.to_csv(OUT+'T3_discrimination_calibration.csv',index=False); print("T3 discrimination/calibration:\n",t3.to_string(index=False))

# ---- integer score (lactate) + categories + bootstrap ----
RC={'lactate':[-1,2,4,99],'ag':[-1,12,18,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}; PR={'uo':[-1,0.5,1.0,99]}; BIN={'ohca_arrest'}
def integ(df,perf):
    feats=[perf,'uo','ohca_arrest','age','bun','rdw']; parts=[]
    for c in feats:
        if c=='ohca_arrest': parts.append(df[c].fillna(0).astype(int).values*3)
        elif c in PR:
            o=pd.cut(df[c],bins=PR[c],labels=False); o=o.fillna(o.median()); parts.append((o.max()-o).astype(int).values)
        else:
            o=pd.cut(df[c],bins=RC[c],labels=False); o=o.fillna(o.median()); parts.append(o.astype(int).values*(2 if c==perf else 1))
    return np.sum(parts,axis=0)
sc=integ(d,'lactate')
# bootstrap optimism (re-derive points each boot via ordinal logistic) - reuse integer AUROC
def ord_pts(df,perf,yy):
    feats=[perf,'uo','ohca_arrest','age','bun','rdw']; O=[]
    for c in feats:
        if c=='ohca_arrest': O.append(df[c].fillna(0).astype(int).values)
        elif c in PR:
            o=pd.cut(df[c],bins=PR[c],labels=False); o=o.fillna(o.median()); O.append((o.max()-o).astype(int).values)
        else:
            o=pd.cut(df[c],bins=RC[c],labels=False); o=o.fillna(o.median()); O.append(o.astype(int).values)
    O=np.column_stack(O); m=LogisticRegression(max_iter=800).fit(O,yy); B=np.median(np.abs(m.coef_[0]))
    return O,np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
O,pts=ord_pts(d,'lactate',y); app=roc_auc_score(y,(O*pts).sum(1)); opt=[]
for b in range(500):
    ix=np.random.randint(0,len(y),len(y)); _,pb=ord_pts(d.iloc[ix],'lactate',y[ix])
    opt.append(roc_auc_score(y[ix],(O[ix]*pb).sum(1))-roc_auc_score(y,(O*pb).sum(1)))
print(f"\nInteger AUROC {app:.4f}, optimism {np.mean(opt):+.4f}, corrected {app-np.mean(opt):.4f}")

# categories MIMIC vs eICU (lactate + AG), same frozen cutpoints
def cat_table():
    rows=[]; sc_m=integ(d,'lactate'); sc_el=integ(e,'lactate'); sc_eag=integ(e,'ag')
    BND=[(0,3,'Low'),(4,5,'Moderate'),(6,7,'High'),(8,99,'Very High')]
    for lo,hi,lab in BND:
        mm=(sc_m>=lo)&(sc_m<=hi); el=(sc_el>=lo)&(sc_el<=hi); ea=(sc_eag>=lo)&(sc_eag<=hi)
        rows.append({'category':lab,'score':f"{lo}-{hi if hi<99 else '15'}",'MIMIC':f"{y[mm].mean():.1%}",
                     'eICU_lactate':f"{ye[el].mean():.1%}",'eICU_AG':f"{ye[ea].mean():.1%}"})
    return pd.DataFrame(rows)
t4=cat_table(); t4.to_csv(OUT+'T4_risk_categories.csv',index=False); print("\nT4 risk categories:\n",t4.to_string(index=False))

# ---- comparators (BOS,MA2 harmonized AG) ----
em=e.merge(cmp,on='patientunitstayid',how='left')
RISK={0:0.005,1:0.014,2:0.039,3:0.10,4:0.235,5:0.46,6:0.702}
def bm(r):
    if any(pd.isna(r[c]) for c in ['bun_max','spo2_min','sbp_min','age','aniongap_max']): return np.nan
    return int(sum(bool(c) for c in [r['bun_max']>=25,r['spo2_min']<88,r['sbp_min']<80,r['mech_vent']==1,r['age']>=60,r['aniongap_max']>=14]))
em['bm']=em.apply(bm,axis=1)
pe_ag=frozen(['ag']+COM)
crows=[{'model':'CS-MORT-6-AG','scorable':'50% all six observed / 95% AG term / 100% imputed','AUROC':round(roc_auc_score(ye,pe_ag),3)},
       {'model':'BOS,MA2','scorable':f"{em['bm'].notna().mean():.0%} complete","AUROC":round(roc_auc_score(ye[em['bm'].notna()],em['bm'].dropna()),3)}]
t5=pd.DataFrame(crows); t5.to_csv(OUT+'T5_comparators.csv',index=False); print("\nT5 comparators:\n",t5.to_string(index=False))
print("\nALL TABLES SAVED to outputs/tables/")
