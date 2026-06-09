import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
np.random.seed(42)
b=pd.read_csv('/tmp/feat_baseline.csv'); b=b[b['in_primary_cohort']==1]; y=b['in_hospital_mortality'].astype(int).values
cv=StratifiedKFold(5,shuffle=True,random_state=42)
def auc(cols):
    Z=b[cols].astype(float)
    for c in cols: lo,hi=Z[c].quantile(.01),Z[c].quantile(.99); Z[c]=Z[c].clip(lo,hi)
    return cross_val_score(LogisticRegression(max_iter=800,C=0.5),StandardScaler().fit_transform(SimpleImputer(strategy='median').fit_transform(Z)),y,cv=cv,scoring='roc_auc').mean()
rest=['uo_rate_mlkghr','ohca_arrest','age','bun_max','rdw_max','bilirubin_total_max']
print(f"  availability: lactate {b['lactate_max'].notna().mean():.0%}  |  anion gap {b['aniongap_max'].notna().mean():.0%}")
print(f"  CS-MORT-7 with LACTATE:    AUROC {auc(rest+['lactate_max']):.3f}")
print(f"  CS-MORT-7 with ANION GAP:  AUROC {auc(rest+['aniongap_max']):.3f}")
print(f"  with BOTH (lactate+AG):    AUROC {auc(rest+['lactate_max','aniongap_max']):.3f}")
# univariate
from sklearn.metrics import roc_auc_score
for f in ['lactate_max','aniongap_max']:
    v=b[f].fillna(b[f].median()); print(f"    univariate {f}: AUROC {max(roc_auc_score(y,v),1-roc_auc_score(y,v)):.3f}")
