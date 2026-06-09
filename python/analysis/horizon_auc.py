import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
d=pd.read_csv('/tmp/horizon.csv')
feats=['age','hf_cs','ohca_arrest','lactate','sbp','bun','creatinine','albumin','bilirubin','rdw','gcs']
cv=StratifiedKFold(5,shuffle=True,random_state=42)
print(f"{'Horizon':>8} {'N alive':>8} {'deaths':>7} {'lactate avail':>14} {'CV AUROC':>9}")
for T in [6,12,24,48]:
    s=d[(d.horizon_h==T)&(d.alive_at_T==1)].copy()
    y=s['in_hospital_mortality'].astype(int).values
    X=s[feats].astype(float)
    for c in feats:
        lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    Xi=SimpleImputer(strategy='median').fit_transform(X); Xs=StandardScaler().fit_transform(Xi)
    auc=cross_val_score(LogisticRegression(max_iter=800),Xs,y,cv=cv,scoring='roc_auc').mean()
    lac_av=s['lactate'].notna().mean()
    print(f"{T:>6}h {len(s):>8} {y.sum():>7} {lac_av:>13.0%} {auc:>9.3f}")
