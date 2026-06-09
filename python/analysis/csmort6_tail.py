# CS-MORT-6 result-tail refresh from canonical tables: DeLong vs BOS,MA2,
# 30-day secondary, integer calibration data, DCA inputs.
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
from scipy import stats
np.random.seed(42); OUT='outputs/tables/'
d=pd.read_csv(OUT+'cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
y=d['in_hospital_mortality'].astype(int).values; y30=d['dead_30d'].astype(int).values
e=pd.read_csv(OUT+'cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'}); ye=e['hosp_mort'].astype(int).values
cmp=pd.read_csv(OUT+'cs_eicu_comparators.csv'); COM=['uo','ohca_arrest','age','bun','rdw']  # canonical: sql/05_eicu_comparators.sql
def _mid(x):
    J=np.argsort(x); Z=x[J]; N=len(x); T=np.zeros(N); i=0
    while i<N:
        j=i
        while j<N and Z[j]==Z[i]: j+=1
        T[i:j]=0.5*(i+j-1)+1; i=j
    o=np.empty(N); o[J]=T; return o
def delong(yv,p1,p2):
    yv=np.asarray(yv); pos=yv==1; neg=yv==0; m=pos.sum(); n=neg.sum(); pr=np.vstack([p1,p2])
    tx=np.array([_mid(pr[k][pos]) for k in range(2)]); ty=np.array([_mid(pr[k][neg]) for k in range(2)]); tz=np.array([_mid(pr[k]) for k in range(2)])
    aucs=(tz[:,pos].sum(1)-m*(m+1)/2)/(m*n); v01=(tz[:,pos]-tx)/n; v10=1-(tz[:,neg]-ty)/m
    S=np.cov(v01)/m+np.cov(v10)/n; var=S[0,0]+S[1,1]-2*S[0,1]
    z=(aucs[0]-aucs[1])/np.sqrt(var) if var>0 else 0.0; return aucs[0],aucs[1],2*stats.norm.sf(abs(z))
def frozen(cols):
    X=d[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1)
    m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X,y)
    Xe=e[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1); return m.predict_proba(Xe)[:,1]
# ---- DeLong: AG-6 vs BOS,MA2 (canonical) ----
em=e.merge(cmp,on='patientunitstayid',how='left')
def bm(r):
    if any(pd.isna(r[c]) for c in ['bun_max','spo2_min','sbp_min','age','aniongap_max']): return np.nan
    return int(sum(bool(c) for c in [r['bun_max']>=25,r['spo2_min']<88,r['sbp_min']<80,r['mech_vent']==1,r['age']>=60,r['aniongap_max']>=14]))
em['bm']=em.apply(bm,axis=1); both=em['bm'].notna().values
pag=frozen(['ag']+COM)
a1,a2,p=delong(ye[both],pag[both],em['bm'].dropna().values)
print(f"DeLong (n={both.sum()}): CS-MORT-6-AG {a1:.3f} vs BOS,MA2 {a2:.3f}, diff {a1-a2:+.3f}, p={p:.3f}")
# ---- 30-day secondary (canonical) ----
def cv(yv,cols):
    X=d[cols].astype(float).clip(d[cols].quantile(.01),d[cols].quantile(.99),axis=1); pp=np.zeros(len(yv))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=42).split(X,yv):
        m=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X.iloc[tr],yv[tr]); pp[te]=m.predict_proba(X.iloc[te])[:,1]
    return pp
p30=cv(y30,['lactate']+COM)
print(f"30-day CS-MORT-6 CV AUROC {roc_auc_score(y30,p30):.3f} (in-hosp {roc_auc_score(y,cv(y,['lactate']+COM)):.3f}); 30-day mort {y30.mean():.1%}")
# ---- integer score -> calibration data (observed mortality per integer score) ----
RC={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}; PR={'uo':[-1,0.5,1.0,99]}
parts=[]; F6=['lactate','uo','ohca_arrest','age','bun','rdw']
for c in F6:
    if c=='ohca_arrest': parts.append(d[c].fillna(0).astype(int).values*3)
    elif c in PR:
        o=pd.cut(d[c],bins=PR[c],labels=False); o=o.fillna(o.median()); parts.append((o.max()-o).astype(int).values)
    else:
        o=pd.cut(d[c],bins=RC[c],labels=False); o=o.fillna(o.median()); parts.append(o.astype(int).values*(2 if c=='lactate' else 1))
sc=np.sum(parts,axis=0)
g=pd.DataFrame({'score':sc,'y':y}).groupby('score').agg(n=('y','size'),obs=('y','mean')).reset_index()
g.to_csv(OUT+'integer_calibration_mimic.csv',index=False)
# DCA inputs (CS-MORT-6 internal CV preds + eICU AG + BOS,MA2)
pd.DataFrame({'p':cv(y,['lactate']+COM),'y':y}).to_csv(OUT+'dca_mimic_cm6.csv',index=False)
em['p_ag']=pag; em[['p_ag','bm']].assign(y=ye).to_csv(OUT+'dca_eicu_cm6.csv',index=False)
print("saved: integer_calibration_mimic.csv, dca_mimic_cm6.csv, dca_eicu_cm6.csv")
