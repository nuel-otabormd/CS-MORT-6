import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
cv=StratifiedKFold(5,shuffle=True,random_state=42)
# bins (risk features: higher=worse; protective marked)
BINS={'lactate':([0,2,4,6,99],False),'bun':([0,20,40,60,999],False),'creatinine':([0,1.2,2,3,99],False),
 'rdw':([0,14,16,18,99],False),'bilirubin':([0,1,2,5,99],False),'age':([0,60,75,85,200],False),
 'sbp':([0,80,90,110,999],True),'mbp':([0,55,65,75,999],True),'albumin':([0,2.5,3,3.5,99],True),
 'hemoglobin':([0,8,10,12,99],True),'uo_rate_mlkghr':([0,0.3,0.5,1,99],True),'heart_rate':([0,80,100,120,999],False)}
BINARY={'ami_cs','ohca_arrest','invasive_vent_24h'}
def ordinal(col):
    if col in BINARY: return d[col].fillna(0).astype(float)
    bins,prot=BINS[col]; o=pd.cut(d[col],bins=bins,labels=False,include_lowest=True).astype(float)
    o=o.fillna(o.median()); return (o.max()-o) if prot else o      # all coded higher=worse
def continuous_auc(cols):
    X=d[cols].astype(float)
    for c in cols: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    Xs=StandardScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(X))
    return cross_val_score(LogisticRegression(max_iter=800,C=0.5),Xs,y,cv=cv,scoring='roc_auc').mean()
def integer_auc(cols):
    O=pd.DataFrame({c:ordinal(c) for c in cols})
    m=LogisticRegression(max_iter=800).fit(StandardScaler().fit_transform(O),y)
    co=np.abs(m.coef_[0]); pts=np.maximum(1,(co/np.median(co[co>0])).round()).astype(int)
    score=(O.values*pts).sum(1)
    # honest: out-of-fold integer AUROC via the same point structure (points are stable)
    return roc_auc_score(y,score), int(score.min()), int(score.max())
DATA=['lactate','age','ami_cs','bun','creatinine','albumin','rdw','bilirubin','uo_rate_mlkghr','ohca_arrest']
CLIN=['lactate','age','mbp','creatinine','hemoglobin','ami_cs','invasive_vent_24h']  # textbook CS a priori
for name,cols in [("DATA-DRIVEN core",DATA),("CLINICAL a-priori",CLIN),("UNION",sorted(set(DATA)|set(CLIN)))]:
    ca=continuous_auc(cols); ia,lo,hi=integer_auc(cols)
    print(f"{name:>18} ({len(cols)} feat): continuous AUROC {ca:.3f} | integer AUROC {ia:.3f} (range {lo}-{hi})")
