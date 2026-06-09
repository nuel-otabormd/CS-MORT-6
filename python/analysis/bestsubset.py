import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, itertools
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
# reduced pool: strongest distinct candidates (incl. collinear acid-base/renal members so search can choose the best representative)
pool=['lactate','ph','uo_rate_mlkghr','bun','creatinine','age','rdw','albumin','ohca_arrest','bilirubin','glucose','sbp','ast','inr']
X=d[pool].astype(float)
for c in pool: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
Xi=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X),columns=pool)
Xs=pd.DataFrame(StandardScaler().fit_transform(Xi),columns=pool)
cv=StratifiedKFold(5,shuffle=True,random_state=42)
lr=LogisticRegression(max_iter=400,C=0.5)
res=[]
for combo in itertools.combinations(pool,8):
    a=cross_val_score(lr,Xs[list(combo)],y,cv=cv,scoring='roc_auc').mean()
    res.append((a,combo))
res.sort(reverse=True)
print(f"searched {len(res)} 8-feature combinations\n")
print("TOP 5 best-subset combinations (CV AUROC):")
for a,combo in res[:5]: print(f"  {a:.4f}  {list(combo)}")
rank8=['lactate','uo_rate_mlkghr','ohca_arrest','age','bun','albumin','rdw','bilirubin']
ra=cross_val_score(lr,Xs[rank8],y,cv=cv,scoring='roc_auc').mean()
print(f"\nRanking-based 8 (current score): {ra:.4f}  {rank8}")
print(f"Best-subset gain over ranking: +{res[0][0]-ra:.4f}")
