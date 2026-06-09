import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
np.random.seed(42)

EXCLUDE = {'stay_id','subject_id','hadm_id','in_hospital_mortality','dead_30d','died_before_24h',
           'in_primary_cohort','in_core_cohort','in_documented_only','present_at_24h','present_at_48h',
           'present_at_72h','anchor_year_group','cs_etiology','non_ami_cs',
           'sofa_24h','apsiii','sapsii','oasis','charlson_comorbidity_index','scai_cswg_stage'}
# REMOVE anion gap (lactate proxy) per EO; keep collinear drops as before
DROP = {'renal_disease','urineoutput_24h','alt_max','preadm_creatinine','baseexcess_min','aniongap_max'}

base = pd.read_csv('/tmp/feat_baseline.csv')
base['gender'] = (base['gender']=='M').astype(int)
base['nee_max'] = base['nee_max'].fillna(0)

def run(df, label, add_indicator=False):
    df = df.copy()
    feat = [c for c in df.columns if c not in EXCLUDE and c not in DROP and df[c].dtype!='object']
    X = df[feat].astype(float)
    for c in feat:
        lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    if add_indicator:
        X['lactate_missing'] = df['lactate_max'].isna().astype(int); feat=feat+['lactate_missing']
    Xi = pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X), columns=feat)
    Xs = StandardScaler().fit_transform(Xi)
    y = df['in_hospital_mortality'].astype(int).values
    B=400; counts=np.zeros(len(feat))
    for i in range(B):
        idx=np.random.choice(len(y),len(y),replace=True)
        m=LogisticRegression(penalty='l1',solver='liblinear',C=0.1,max_iter=500).fit(Xs[idx],y[idx])
        counts+=(np.abs(m.coef_[0])>1e-6)
    stab=pd.Series(counts/B,index=feat).sort_values(ascending=False)
    rank = list(stab.index).index('lactate_max')+1
    # univariate lactate AUROC on complete lactate
    cc = df.dropna(subset=['lactate_max'])
    ua = roc_auc_score(cc['in_hospital_mortality'], cc['lactate_max'].clip(*cc['lactate_max'].quantile([.01,.99])))
    print(f"\n[{label}] n={len(df)}  lactate_max selection freq = {stab['lactate_max']:.2f} (rank {rank}/{len(feat)})  | univariate lactate AUROC={ua:.3f}")
    if add_indicator: print(f"          lactate_missing indicator freq = {stab['lactate_missing']:.2f}")
    print("   top 10:", [f"{k}({v:.2f})" for k,v in stab.head(10).items()])

run(base, "A: full cohort, AG removed, +missingness indicator", add_indicator=True)
run(base.dropna(subset=['lactate_max']), "B: lactate-COMPLETE cases, AG removed")
