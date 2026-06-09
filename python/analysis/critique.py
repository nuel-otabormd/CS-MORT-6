import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
cv=StratifiedKFold(5,shuffle=True,random_state=42)
def auc(cols):
    X=d[cols].astype(float)
    for c in cols: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    Xs=StandardScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(X))
    return cross_val_score(LogisticRegression(max_iter=800,C=0.5),Xs,y,cv=cv,scoring='roc_auc').mean()
core=['lactate','age','ami_cs','bun','creatinine','albumin','rdw','gcs','bilirubin','uo_rate_mlkghr']
print("== OHCA marginal value ==")
print(f"  core (no OHCA):      AUROC {auc(core):.3f}")
print(f"  core + OHCA:         AUROC {auc(core+['ohca_arrest']):.3f}")
# OHCA effect alone vs after adjusting for GCS (redundancy?)
def orr(cols, target):
    X=d[cols].astype(float).fillna(d[cols].median()); Xs=StandardScaler().fit_transform(X)
    m=LogisticRegression(max_iter=800).fit(Xs,y); return np.exp(m.coef_[0][cols.index(target)])
print(f"  OHCA OR alone:       {orr(['ohca_arrest'],'ohca_arrest'):.2f}")
print(f"  OHCA OR | +GCS:      {orr(['ohca_arrest','gcs'],'ohca_arrest'):.2f}  (corr OHCA~GCS={d['ohca_arrest'].corr(d['gcs']):.2f})")
print("\n== GCS confounded by sedation/ventilation? ==")
for lab,mask in [('NON-vented',d['invasive_vent_24h']==0),('VENTED',d['invasive_vent_24h']==1)]:
    s=d[mask]; ys=s['in_hospital_mortality'].astype(int)
    g=s['gcs'].fillna(s['gcs'].median())
    from sklearn.metrics import roc_auc_score
    print(f"  {lab:>10} (n={len(s)}): median GCS={s['gcs'].median():.0f}, univariate GCS AUROC={roc_auc_score(ys,-g):.3f}")
print(f"\n  core with GCS:    AUROC {auc(core):.3f}")
print(f"  core without GCS: AUROC {auc([c for c in core if c!='gcs']):.3f}")
