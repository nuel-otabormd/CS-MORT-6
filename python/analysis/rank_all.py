import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv'); y=d['in_hospital_mortality'].astype(int).values
feat=[c for c in d.columns if c not in {'stay_id','in_hospital_mortality'} and d[c].dtype!='object']
X=d[feat].astype(float)
for c in feat: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
Xi=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X),columns=feat); Xs=StandardScaler().fit_transform(Xi)
# stability selection
B=400; cnt=np.zeros(len(feat))
for i in range(B):
    idx=np.random.choice(len(y),len(y),replace=True)
    cnt+=(np.abs(LogisticRegression(penalty='l1',solver='liblinear',C=0.3,max_iter=500).fit(Xs[idx],y[idx]).coef_[0])>1e-6)
stab=cnt/B
# univariate AUROC + OR
rows=[]
for j,c in enumerate(feat):
    v=Xi[c].values
    a=roc_auc_score(y,v); a=max(a,1-a)
    orr=np.exp(LogisticRegression(max_iter=500).fit(Xs[:,[j]],y).coef_[0][0])
    rows.append((c,stab[j],a,orr))
FINAL8={'lactate','uo_rate_mlkghr','ohca_arrest','age','bun','albumin','rdw','bilirubin'}
r=pd.DataFrame(rows,columns=['feature','stability','univ_AUROC','OR']).sort_values(['stability','univ_AUROC'],ascending=False).reset_index(drop=True)
print(f"{'rank':>4} {'feature':>22} {'stability':>9} {'univ_AUROC':>10} {'OR':>6}  {'final-8'}")
for i,row in r.iterrows():
    star='  *** IN SCORE' if row['feature'] in FINAL8 else ''
    print(f"{i+1:>4} {row['feature']:>22} {row['stability']:>9.2f} {row['univ_AUROC']:>10.3f} {row['OR']:>6.2f}{star}")
