import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, brier_score_loss
np.random.seed(42)
# principled pre-filter: composites, computed, confounded/near-outcome, collinear dups
EXCLUDE={'stay_id','subject_id','hadm_id','in_hospital_mortality','dead_30d','died_before_24h','in_primary_cohort',
 'in_core_cohort','in_documented_only','present_at_24h','present_at_48h','present_at_72h','anchor_year_group',
 'cs_etiology','non_ami_cs','sofa_24h','apsiii','sapsii','oasis','charlson_comorbidity_index','scai_cswg_stage',
 'aniongap_max','spo2_min','resp_rate_max','rhy_asystole','rhy_paced',
 'shock_index','bun_cr_ratio','nlr','nee_max','baseline_creatinine_est',
 'renal_disease','urineoutput_24h','alt_max','preadm_creatinine','baseexcess_min'}
b=pd.read_csv('/tmp/feat_baseline.csv'); b['gender']=(b['gender']=='M').astype(int)
y=b['in_hospital_mortality'].astype(int).values
feat=[c for c in b.columns if c not in EXCLUDE and b[c].dtype!='object']
X=b[feat].astype(float)
for c in feat: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
X['lactate_missing']=b['lactate_max'].isna().astype(int)
print(f"n={len(b)}, events={y.sum()}, candidate features={X.shape[1]}\n")
cv=StratifiedKFold(5,shuffle=True,random_state=42)
def evaluate(model, needs_scale):
    pipe = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), model) if needs_scale else make_pipeline(model)
    p = cross_val_predict(pipe, X, y, cv=cv, method='predict_proba')[:,1]
    auc=roc_auc_score(y,p); brier=brier_score_loss(y,p)
    # calibration slope: logit(p) -> y
    lp=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    slope=LogisticRegression().fit(lp.reshape(-1,1),y).coef_[0][0]
    return auc, brier, slope
models=[
 ("Elastic-net LR", LogisticRegression(penalty='elasticnet',solver='saga',l1_ratio=0.5,C=0.3,max_iter=3000), True),
 ("Ridge LR",       LogisticRegression(penalty='l2',C=0.3,max_iter=2000), True),
 ("LASSO LR",       LogisticRegression(penalty='l1',solver='liblinear',C=0.3,max_iter=2000), True),
 ("Random Forest",  RandomForestClassifier(n_estimators=400,max_depth=6,min_samples_leaf=20,random_state=42), False),
 ("Grad Boosting",  HistGradientBoostingClassifier(learning_rate=0.05,max_iter=300,max_leaf_nodes=15,l2_regularization=1.0,random_state=42), False),
]
print(f"{'Method':>16} {'AUROC':>7} {'Brier':>7} {'CalSlope':>9}  (ideal slope=1.0)")
for name,m,sc in models:
    a,br,sl=evaluate(m,sc); print(f"{name:>16} {a:>7.3f} {br:>7.3f} {sl:>9.2f}")
