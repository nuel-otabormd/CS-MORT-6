import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
core=['lactate','age','bun','rdw','albumin','gcs','bilirubin','uo_rate_mlkghr','ohca_arrest']
cv=StratifiedKFold(5,shuffle=True,random_state=42)
for etio in ['hf_cs','ami_cs','non_ami_cs']:
    cols=core+[etio]
    X=d[cols].astype(float)
    for c in cols: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    Xi=SimpleImputer(strategy='median').fit_transform(X); Xs=StandardScaler().fit_transform(Xi)
    auc=cross_val_score(LogisticRegression(max_iter=800,C=0.5),Xs,y,cv=cv,scoring='roc_auc').mean()
    co=LogisticRegression(max_iter=800).fit(Xs,y).coef_[0][-1]
    print(f"  etiology={etio:>12}: CV AUROC={auc:.3f}, OR={np.exp(co):.2f}")
