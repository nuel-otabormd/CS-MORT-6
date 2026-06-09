import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
cv=StratifiedKFold(5,shuffle=True,random_state=42)
BINS={'lactate':([0,2,4,6,99],False),'bun':([0,20,40,60,999],False),'rdw':([0,14,16,18,99],False),
 'bilirubin':([0,1,2,5,99],False),'age':([0,60,75,85,200],False),'albumin':([0,2.5,3,3.5,99],True),
 'uo_rate_mlkghr':([0,0.3,0.5,1,99],True),'hemoglobin':([0,8,10,12,99],True)}
BINARY={'ami_cs','ohca_arrest','invasive_vent_24h'}; COUNT={'pressor_count'}
def ordc(col):
    if col in BINARY: return d[col].fillna(0).astype(float)
    if col in COUNT: return d[col].fillna(0).clip(0,3).astype(float)
    bins,prot=BINS[col]; o=pd.cut(d[col],bins=bins,labels=False,include_lowest=True).astype(float); o=o.fillna(o.median())
    return (o.max()-o) if prot else o
def cont(cols):
    Z=d[cols].astype(float)
    for c in cols: lo,hi=Z[c].quantile(.01),Z[c].quantile(.99); Z[c]=Z[c].clip(lo,hi)
    s=cross_val_score(LogisticRegression(max_iter=800,C=0.5),StandardScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(Z)),y,cv=cv,scoring='roc_auc')
    return s.mean(), s.std()
def integ(cols):
    O=pd.DataFrame({c:ordc(c) for c in cols}); m=LogisticRegression(max_iter=800).fit(StandardScaler().fit_transform(O),y)
    a=np.abs(m.coef_[0]); pts=np.maximum(1,(a/np.median(a[a>0])).round()).astype(int)
    return roc_auc_score(y,(O.values*pts).sum(1))
OLD=['lactate','uo_rate_mlkghr','age','bun','invasive_vent_24h','ami_cs','pressor_count','hemoglobin']
NEW=['lactate','uo_rate_mlkghr','ohca_arrest','age','bun','albumin','rdw','bilirubin']
print("OLD CS-MORT-8 vars:", OLD)
print("NEW CS-MORT-8 vars:", NEW, "\n")
for name,cols in [("OLD CS-MORT-8",OLD),("NEW (data-driven 8)",NEW)]:
    cm,cs=cont(cols); print(f"  {name:>22}: continuous AUROC {cm:.3f} (+/-{cs:.3f}) | integer {integ(cols):.3f}")
