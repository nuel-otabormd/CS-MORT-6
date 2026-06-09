import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

EXCLUDE = {'stay_id','subject_id','hadm_id','in_hospital_mortality','dead_30d','died_before_24h',
           'in_primary_cohort','in_core_cohort','in_documented_only','present_at_24h','present_at_48h',
           'present_at_72h','anchor_year_group','cs_etiology','non_ami_cs'}

def prep(df):
    df = df.copy()
    if 'gender' in df.columns: df['gender'] = (df['gender']=='M').astype(int)
    stage_map = {'A':1,'B':2,'C':3,'D':4,'E':5}
    if 'scai_cswg_stage' in df: df['scai_cswg_stage'] = df['scai_cswg_stage'].map(stage_map)
    if 'scai_cswg_stage_48h' in df: df['scai_cswg_stage_48h'] = df['scai_cswg_stage_48h'].map(stage_map)
    if 'nee_max' in df: df['nee_max'] = df['nee_max'].fillna(0)   # null NEE = no pressor
    return df

def winsor(X):
    for c in X.columns:
        lo,hi = X[c].quantile(0.01), X[c].quantile(0.99)
        X[c] = X[c].clip(lo,hi)
    return X

def auc_cv(X, y, model, n=5):
    cv = StratifiedKFold(n, shuffle=True, random_state=42)
    s = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    return s.mean(), s.std()

# ---------- BASELINE ----------
b = prep(pd.read_csv('/tmp/feat_baseline.csv'))
y = b['in_hospital_mortality'].astype(int)
feat = [c for c in b.columns if c not in EXCLUDE and b[c].dtype!='object']
X = winsor(b[feat].astype(float))
print(f"BASELINE: n={len(b)}, events={y.sum()} ({y.mean():.1%}), n_features={len(feat)}")

lr = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
gb = HistGradientBoostingClassifier(random_state=42, max_iter=300, learning_rate=0.05)
m,s = auc_cv(X,y,lr); print(f"  Logistic regression  5-fold CV AUROC = {m:.3f} (+/-{s:.3f})")
m,s = auc_cv(X,y,gb); print(f"  HistGradientBoosting  5-fold CV AUROC = {m:.3f} (+/-{s:.3f})")

# top collinear pairs
corr = X.corr().abs()
pairs=[]
for i in range(len(feat)):
    for j in range(i+1,len(feat)):
        if corr.iloc[i,j]>0.8: pairs.append((feat[i],feat[j],round(corr.iloc[i,j],2)))
print(f"  Collinear pairs |r|>0.8: {len(pairs)}")
for p in sorted(pairs,key=lambda x:-x[2])[:8]: print("     ",p)

# missingness of key features
miss = (b[feat].isna().mean().sort_values(ascending=False))
print("  Highest missingness:", {k:round(v,2) for k,v in miss.head(6).items()})

# ---------- DYNAMIC value at landmark-2 ----------
d = prep(pd.read_csv('/tmp/feat_dynamic.csv'))
dyn_feats = ['lactate_clearance_frac','delta_lactate_max','delta_nee','vaso_escalation','delta_creatinine',
             'new_af','new_vt_vf','new_arrest','new_rrt_incident','new_mcs','scai_cswg_stage_48h','scai_escalation']
dyn_feats = [c for c in dyn_feats if c in d.columns]
m2 = b.merge(d[['stay_id']+dyn_feats], on='stay_id', how='inner')
y2 = m2['in_hospital_mortality'].astype(int)
Xb = winsor(m2[feat].astype(float))                      # baseline-only, landmark-2 patients
Xbd = winsor(m2[feat+dyn_feats].astype(float))           # baseline + dynamic
print(f"\nLANDMARK-2 (alive at 48h): n={len(m2)}, events={y2.sum()} ({y2.mean():.1%})")
mb,_ = auc_cv(Xb,y2,gb);  print(f"  Baseline-only            CV AUROC = {mb:.3f}")
mbd,_= auc_cv(Xbd,y2,gb); print(f"  Baseline + DYNAMIC       CV AUROC = {mbd:.3f}   (delta +{mbd-mb:.3f})")
