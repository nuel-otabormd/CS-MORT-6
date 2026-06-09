import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
# CS-MORT-7 with clinical cut-points (higher category = worse). Protective feats coded so low value = worse.
CUT={ # feature:(bin edges, labels low->high RISK)
 'lactate':[-1,2,4,6,99],          # <2,2-4,4-6,>=6
 'bun':[-1,20,40,60,999],          # <20,20-40,40-60,>=60
 'rdw':[-1,14,16,18,99],           # <14,14-16,16-18,>=18
 'bilirubin':[-1,1,2,5,99],        # <1,1-2,2-5,>=5
 'age':[-1,60,75,85,200]}          # <60,60-74,75-84,>=85
PROT={'uo_rate_mlkghr':[-1,0.5,1,99]}  # >=1,0.5-1,<0.5 -> reverse
BIN={'ohca_arrest'}
def ordc(f):
    if f in BIN: return d[f].fillna(0).astype(int)
    if f in PROT:
        o=pd.cut(d[f],bins=PROT[f],labels=False); o=o.fillna(o.median()); return (o.max()-o).astype(int) # reverse
    o=pd.cut(d[f],bins=CUT[f],labels=False); return o.fillna(o.median()).astype(int)
feats=['lactate','uo_rate_mlkghr','ohca_arrest','age','bun','rdw','bilirubin']
O=pd.DataFrame({f:ordc(f) for f in feats})
m=LogisticRegression(max_iter=800).fit(O,y)   # coef per ordinal step
B=np.median(np.abs(m.coef_[0]))               # scaling constant
pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
print("=== CS-MORT-7 INTEGER POINTS (per category step) ===")
for f,p in zip(feats,pts):
    nstep=int(O[f].max()); print(f"  {f:>16}: {p} pts/step  (categories 0..{nstep}, max {p*nstep} pts)")
score=(O.values*pts).sum(1)
print(f"  TOTAL SCORE RANGE: {score.min()}-{score.max()}")
# integer AUROC (in-sample) + cross-validated probability-from-score
auc_in=roc_auc_score(y,score)
cvp=cross_val_predict(LogisticRegression(max_iter=500),score.reshape(-1,1),y,cv=StratifiedKFold(5,shuffle=True,random_state=42),method='predict_proba')[:,1]
print(f"  INTEGER AUROC: {auc_in:.3f} (in-sample) | {roc_auc_score(y,cvp):.3f} (CV via score->risk)")
# risk categories by clinical-anchored thresholds, check MONOTONIC gradient
d['score']=score
for thr,lab in [((score<=score.max()*0.25),'Q-thresholds')]: pass
cats=pd.cut(score,bins=[-1, np.percentile(score,25), np.percentile(score,50), np.percentile(score,75), 999],
           labels=['Low','Moderate','High','VeryHigh'])
print("\n=== RISK CATEGORIES (MIMIC) — monotonic gradient check ===")
prev=-1; mono=True
for c in ['Low','Moderate','High','VeryHigh']:
    mk=cats==c; mr=y[mk].mean()
    if mr<prev: mono=False
    prev=mr
    print(f"   {c:>9}: score {int(score[mk].min())}-{int(score[mk].max())}, n={mk.sum()}, mortality {mr:.1%}")
print(f"   MONOTONIC: {mono}")
