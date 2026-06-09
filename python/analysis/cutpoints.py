import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
cont=['lactate','bun','age','rdw','bilirubin','uo_rate_mlkghr']
print("=== WHAT THE DATA SAYS: mortality across QUINTILES of each feature ===")
for f in cont:
    v=d[f]; q=pd.qcut(v,5,duplicates='drop')
    g=pd.DataFrame({'q':q,'y':y}).groupby('q',observed=True)
    edges=[f"{iv.right:.1f}" for iv in g.groups.keys()][:-1]
    morts=[f"{g.get_group(k)['y'].mean():.0%}" for k in g.groups]
    print(f"  {f:>16}: cut at {edges}  -> mortality {morts}")
# integer AUROC: data-driven QUINTILE coding vs my clinical cut-points
def integ_auc(coder):
    O=pd.DataFrame({f:coder(f) for f in cont}); O['ohca']=d['ohca_arrest'].fillna(0)
    m=LogisticRegression(max_iter=800).fit(O,y); B=np.median(np.abs(m.coef_[0]))
    pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int); s=(O.values*pts).sum(1)
    return roc_auc_score(y, cross_val_predict(LogisticRegression(max_iter=500),s.reshape(-1,1),y,cv=StratifiedKFold(5,shuffle=True,random_state=42),method='predict_proba')[:,1])
prot={'uo_rate_mlkghr'}
def quintile(f):  # purely data-driven, 5 groups
    o=pd.qcut(d[f],5,labels=False,duplicates='drop').fillna(2).astype(int); return (o.max()-o) if f in prot else o
CLIN={'lactate':[-1,2,4,6,99],'bun':[-1,20,40,60,999],'age':[-1,60,75,85,200],'rdw':[-1,14,16,18,99],'bilirubin':[-1,1,2,5,99],'uo_rate_mlkghr':[-1,0.5,1,99]}
def clinical(f):
    o=pd.cut(d[f],bins=CLIN[f],labels=False); o=o.fillna(o.median()).astype(int); return (o.max()-o) if f in prot else o
print(f"\n  Integer AUROC, DATA-DRIVEN quintile cut-points: {integ_auc(quintile):.3f}")
print(f"  Integer AUROC, my CLINICAL round-number cuts:   {integ_auc(clinical):.3f}")
print(f"  Continuous (no categorization) reference:        ~0.781")
