import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
np.random.seed(42)

EXCLUDE = {'stay_id','subject_id','hadm_id','in_hospital_mortality','dead_30d','died_before_24h',
           'in_primary_cohort','in_core_cohort','in_documented_only','present_at_24h','present_at_48h',
           'present_at_72h','anchor_year_group','cs_etiology','non_ami_cs',
           'sofa_24h','apsiii','sapsii','oasis','charlson_comorbidity_index','scai_cswg_stage'}
# collinear duplicates to drop (keep the more interpretable/available of each |r|>0.8 pair)
DROP_COLLINEAR = {'renal_disease','urineoutput_24h','alt_max','preadm_creatinine','baseexcess_min'}

b = pd.read_csv('/tmp/feat_baseline.csv')
b['gender'] = (b['gender']=='M').astype(int)
b['scai_cswg_stage'] = b['scai_cswg_stage'].map({'A':1,'B':2,'C':3,'D':4,'E':5})
b['nee_max'] = b['nee_max'].fillna(0)
y = b['in_hospital_mortality'].astype(int).values
feat = [c for c in b.columns if c not in EXCLUDE and c not in DROP_COLLINEAR and b[c].dtype!='object']
X = b[feat].astype(float)
for c in feat:  # winsorize
    lo,hi = X[c].quantile(0.01), X[c].quantile(0.99); X[c]=X[c].clip(lo,hi)
Xi = pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X), columns=feat)
Xs = StandardScaler().fit_transform(Xi)
print(f"n={len(b)}, events={y.sum()}, candidate features after collinearity drop = {len(feat)}\n")

# ---- bootstrap LASSO stability selection ----
B = 400
counts = np.zeros(len(feat))
for i in range(B):
    idx = np.random.choice(len(y), len(y), replace=True)
    m = LogisticRegression(penalty='l1', solver='liblinear', C=0.1, max_iter=500)
    m.fit(Xs[idx], y[idx])
    counts += (np.abs(m.coef_[0]) > 1e-6)
stab = pd.Series(counts/B, index=feat).sort_values(ascending=False)
print("=== STABILITY SELECTION (fraction of 400 bootstraps a feature is selected) ===")
for k,v in stab.head(20).items(): print(f"  {v:5.2f}  {k}")

# ---- parsimony curve: CV AUROC vs top-k stable features ----
print("\n=== PARSIMONY CURVE (ridge LR on top-k stable features) ===")
cv = StratifiedKFold(5, shuffle=True, random_state=42)
order = stab.index.tolist()
for k in [4,5,6,7,8,9,10,12,15]:
    cols = order[:k]
    Xk = StandardScaler().fit_transform(Xi[cols])
    auc = cross_val_score(LogisticRegression(max_iter=1000,C=1.0), Xk, y, cv=cv, scoring='roc_auc').mean()
    print(f"  top {k:2d} features: CV AUROC = {auc:.3f}")

# ---- fit a parsimonious 8-feature model, show ORs ----
k=8; cols=order[:k]
Xk = StandardScaler().fit_transform(Xi[cols])
m = LogisticRegression(max_iter=1000).fit(Xk,y)
print(f"\n=== Parsimonious {k}-feature model (standardized ORs) ===")
for c,coef in sorted(zip(cols, m.coef_[0]), key=lambda x:-abs(x[1])):
    print(f"  OR {np.exp(coef):5.2f}   {c}")
