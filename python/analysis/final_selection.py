import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
np.random.seed(42)
EXCLUDE={'stay_id','subject_id','hadm_id','in_hospital_mortality','dead_30d','died_before_24h','in_primary_cohort',
 'in_core_cohort','in_documented_only','present_at_24h','present_at_48h','present_at_72h','anchor_year_group',
 'cs_etiology','non_ami_cs',
 'sofa_24h','apsiii','sapsii','oasis','charlson_comorbidity_index','scai_cswg_stage',   # composites=comparators
 'aniongap_max','spo2_min','resp_rate_max','rhy_asystole',                              # clinical guardrails
 'renal_disease','urineoutput_24h','alt_max','preadm_creatinine','baseexcess_min'}      # collinear dups
b=pd.read_csv('/tmp/feat_baseline.csv'); b['gender']=(b['gender']=='M').astype(int); b['nee_max']=b['nee_max'].fillna(0)
y=b['in_hospital_mortality'].astype(int).values
feat=[c for c in b.columns if c not in EXCLUDE and b[c].dtype!='object']
X=b[feat].astype(float)
for c in feat: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
X['lactate_missing']=b['lactate_max'].isna().astype(int); feat=feat+['lactate_missing']
Xi=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X),columns=feat); Xs=StandardScaler().fit_transform(Xi)
print(f"n={len(b)}, events={y.sum()}, candidate features={len(feat)}")
B=400; cnt=np.zeros(len(feat))
for i in range(B):
    idx=np.random.choice(len(y),len(y),replace=True)
    cnt+=(np.abs(LogisticRegression(penalty='l1',solver='liblinear',C=0.1,max_iter=500).fit(Xs[idx],y[idx]).coef_[0])>1e-6)
stab=pd.Series(cnt/B,index=feat).sort_values(ascending=False)
print("\n=== STABLE FEATURES (>=0.80 selection) ===")
for k,v in stab[stab>=0.80].items(): print(f"  {v:.2f}  {k}")
cv=StratifiedKFold(5,shuffle=True,random_state=42)
print("\n=== PARSIMONY ===")
for k in [6,7,8,9,10,12,15]:
    cols=stab.index[:k].tolist()
    a=cross_val_score(LogisticRegression(max_iter=800),StandardScaler().fit_transform(Xi[cols]),y,cv=cv,scoring='roc_auc').mean()
    print(f"  top {k:2d}: CV AUROC {a:.3f}")
k=10; cols=stab.index[:k].tolist()
m=LogisticRegression(max_iter=800).fit(StandardScaler().fit_transform(Xi[cols]),y)
print(f"\n=== Parsimonious {k}-feature model (standardized ORs) ===")
for c,co in sorted(zip(cols,m.coef_[0]),key=lambda x:-abs(x[1])): print(f"  OR {np.exp(co):5.2f}  {c}")
