import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
np.random.seed(42)
EXCLUDE = {'stay_id','subject_id','hadm_id','in_hospital_mortality','dead_30d','died_before_24h',
 'in_primary_cohort','in_core_cohort','in_documented_only','present_at_24h','present_at_48h','present_at_72h',
 'anchor_year_group','cs_etiology','non_ami_cs','sofa_24h','apsiii','sapsii','oasis','charlson_comorbidity_index','scai_cswg_stage'}
# clinical guardrail drops: anion gap (lactate proxy), asystole (near-outcome), RR (vent-confounded), collinear dups
DROP = {'renal_disease','urineoutput_24h','alt_max','preadm_creatinine','baseexcess_min','aniongap_max',
        'rhy_asystole','resp_rate_max'}
b = pd.read_csv('/tmp/feat_baseline.csv')   # NOTE: re-export needed for invasive_vent_24h; using current
b['gender']=(b['gender']=='M').astype(int); b['nee_max']=b['nee_max'].fillna(0)
def go(extra_drop, tag):
    drop=DROP|extra_drop
    feat=[c for c in b.columns if c not in EXCLUDE and c not in drop and b[c].dtype!='object']
    X=b[feat].astype(float)
    for c in feat: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    X['lactate_missing']=b['lactate_max'].isna().astype(int); feat=feat+['lactate_missing']
    Xi=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X),columns=feat)
    Xs=StandardScaler().fit_transform(Xi); y=b['in_hospital_mortality'].astype(int).values
    B=300; cnt=np.zeros(len(feat))
    for i in range(B):
        idx=np.random.choice(len(y),len(y),replace=True)
        cnt+=(np.abs(LogisticRegression(penalty='l1',solver='liblinear',C=0.1,max_iter=400).fit(Xs[idx],y[idx]).coef_[0])>1e-6)
    stab=pd.Series(cnt/B,index=feat).sort_values(ascending=False)
    cv=StratifiedKFold(5,shuffle=True,random_state=42)
    aucs={k:cross_val_score(LogisticRegression(max_iter=800),StandardScaler().fit_transform(Xi[stab.index[:k].tolist()]),y,cv=cv,scoring='roc_auc').mean() for k in [8,10,12,15]}
    print(f"[{tag}] top8 stable: {[k for k in stab.index[:8]]}")
    print(f"        parsimony CV AUROC  8:{aucs[8]:.3f} 10:{aucs[10]:.3f} 12:{aucs[12]:.3f} 15:{aucs[15]:.3f}")
go(set(), "drop asystole+RR, KEEP SpO2")
go({'spo2_min'}, "drop asystole+RR+SpO2")
