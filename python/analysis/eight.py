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
BINS={'lactate':([0,2,4,6,99],False),'bun':([0,20,40,60,999],False),'creatinine':([0,1.2,2,3,99],False),
 'rdw':([0,14,16,18,99],False),'bilirubin':([0,1,2,5,99],False),'age':([0,60,75,85,200],False),
 'albumin':([0,2.5,3,3.5,99],True),'uo_rate_mlkghr':([0,0.3,0.5,1,99],True)}
BINARY={'ami_cs','ohca_arrest'}
def ordc(col):
    if col in BINARY: return d[col].fillna(0).astype(float)
    bins,prot=BINS[col]; o=pd.cut(d[col],bins=bins,labels=False,include_lowest=True).astype(float); o=o.fillna(o.median())
    return (o.max()-o) if prot else o
core=['lactate','age','ami_cs','bun','creatinine','albumin','rdw','bilirubin','uo_rate_mlkghr','ohca_arrest']
# rank by standardized coefficient magnitude in the full core model
X=d[core].astype(float)
for c in core: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
Xs=StandardScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(X))
co=LogisticRegression(max_iter=800).fit(Xs,y).coef_[0]
rank=[core[i] for i in np.argsort(-np.abs(co))]
def cont(cols):
    Z=d[cols].astype(float)
    for c in cols: lo,hi=Z[c].quantile(.01),Z[c].quantile(.99); Z[c]=Z[c].clip(lo,hi)
    return cross_val_score(LogisticRegression(max_iter=800,C=0.5),StandardScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(Z)),y,cv=cv,scoring='roc_auc').mean()
def integ(cols):
    O=pd.DataFrame({c:ordc(c) for c in cols}); m=LogisticRegression(max_iter=800).fit(StandardScaler().fit_transform(O),y)
    a=np.abs(m.coef_[0]); pts=np.maximum(1,(a/np.median(a[a>0])).round()).astype(int)
    s=(O.values*pts).sum(1); return roc_auc_score(y,s)
print("feature rank (by importance):", rank)
for k in [6,7,8,9,10]:
    cols=rank[:k]; print(f"  {k} features: continuous {cont(cols):.3f} | integer {integ(cols):.3f}   {'<- 8-FEAT: '+str(rank[:8]) if k==8 else ''}")
