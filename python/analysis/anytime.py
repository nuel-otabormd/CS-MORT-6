import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
d=pd.read_csv('/tmp/horizon_mr.csv')
feats=['age','ami_cs','ohca_arrest','lactate','bun','creatinine','albumin','bilirubin','rdw','gcs','uo_rate']
# Freeze ONE model trained on the 24h snapshot, then apply it at every horizon (true "anytime" test)
tr=d[(d.horizon_h==24)&(d.alive_at_T==1)].copy()
imp=SimpleImputer(strategy='median').fit(tr[feats]); sc=StandardScaler().fit(imp.transform(tr[feats]))
m=LogisticRegression(max_iter=800,C=0.5).fit(sc.transform(imp.transform(tr[feats])), tr['in_hospital_mortality'])
print(f"{'Compute at':>11} {'N alive':>8} {'AUROC (frozen 24h score)':>26}")
for T in [6,12,24,48]:
    s=d[(d.horizon_h==T)&(d.alive_at_T==1)]
    p=m.predict_proba(sc.transform(imp.transform(s[feats])))[:,1]
    print(f"{T:>9}h {len(s):>8} {roc_auc_score(s['in_hospital_mortality'],p):>26.3f}")
