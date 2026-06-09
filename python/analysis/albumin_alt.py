import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
cv=StratifiedKFold(5,shuffle=True,random_state=42)
base7=['lactate','uo_rate_mlkghr','ohca_arrest','age','bun','rdw','bilirubin']  # the 7 without the 8th slot
def auc(cols):
    Z=d[cols].astype(float)
    for c in cols: lo,hi=Z[c].quantile(.01),Z[c].quantile(.99); Z[c]=Z[c].clip(lo,hi)
    return cross_val_score(LogisticRegression(max_iter=800,C=0.5),StandardScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(Z)),y,cv=cv,scoring='roc_auc').mean()
print(f"  7-feature base (no 8th slot): AUROC {auc(base7):.3f}\n")
print(f"{'8th-slot feature':>16} {'AUROC':>7} {'availability':>12} {'clinical axis'}")
cands={'albumin':'hepatic-synth/nutrition (current)','inr':'hepatic-synth/coagulopathy','creatinine':'renal (redundant w/ BUN)',
 'bicarbonate':'acid-base (collinear lactate)','glucose':'stress hyperglycemia','pressor_count':'treatment intensity',
 'mbp':'hemodynamic (pressor-confounded)','ast':'shock liver (redundant w/ bili)','platelets':'DIC/hepatic','wbc':'inflammation'}
for f,axis in cands.items():
    avail=d[f].notna().mean()
    print(f"{f:>16} {auc(base7+[f]):>7.3f} {avail:>11.0%}  {axis}")
