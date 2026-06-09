import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
np.random.seed(42)
d=pd.read_csv('/tmp/feat_mr.csv')
y=d['in_hospital_mortality'].astype(int).values
ID={'stay_id','in_hospital_mortality'}
feat=[c for c in d.columns if c not in ID and d[c].dtype!='object']
X=d[feat].astype(float)
for c in feat: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
Xi=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X),columns=feat); Xs=StandardScaler().fit_transform(Xi)
print(f"MOST-RECENT data: n={len(d)}, events={y.sum()}, candidate features={len(feat)}")
# stability selection
B=400; cnt=np.zeros(len(feat))
for i in range(B):
    idx=np.random.choice(len(y),len(y),replace=True)
    cnt+=(np.abs(LogisticRegression(penalty='l1',solver='liblinear',C=0.3,max_iter=500).fit(Xs[idx],y[idx]).coef_[0])>1e-6)
stab=pd.Series(cnt/B,index=feat).sort_values(ascending=False)
print("\nTOP STABLE FEATURES:", [f"{k}({v:.2f})" for k,v in stab.head(12).items()])
cv=StratifiedKFold(5,shuffle=True,random_state=42)
print("PARSIMONY:", {k:round(cross_val_score(LogisticRegression(max_iter=800,C=0.5),StandardScaler().fit_transform(Xi[stab.index[:k].tolist()]),y,cv=cv,scoring='roc_auc').mean(),3) for k in [8,9,10,12]})

# ---- INTEGER SCORE (Sullivan) on top features w/ clinical bins ----
B_pts={  # (bins, labels-direction): points assigned by fitted coef/scale
 'lactate':[0,2,4,6,99],'bun':[0,20,40,60,999],'creatinine':[0,1.2,2,3,99],
 'rdw':[0,14,16,18,99],'bilirubin':[0,1,2,5,99],'age':[0,60,75,85,200],
 'sbp':[0,80,90,110,999],'albumin':[0,2.5,3,3.5,99],'gcs':[2,8,13,14,16]}
top=[f for f in stab.index[:10] if f in B_pts] + [f for f in ['ohca_arrest','hf_cs','invasive_vent_24h'] if f in stab.index[:14]]
Xb=pd.DataFrame(index=d.index)
for f in top:
    if f in B_pts:
        Xb[f]=pd.cut(Xi[f],bins=B_pts[f],labels=False,include_lowest=True)
    else:
        Xb[f]=Xi[f]
lr=LogisticRegression(max_iter=800).fit(StandardScaler().fit_transform(Xb.fillna(0)),y)
# scale coefs to integer points (smallest |coef| ~ 1 point)
co=np.abs(lr.coef_[0]); base=np.median(co[co>0])
pts=(co/base).round().astype(int)
score=np.zeros(len(d))
for j,f in enumerate(top):
    v=Xb[f].fillna(0).values
    score += pts[j]*(v if lr.coef_[0][j]>0 else (Xb[f].max()-v if f in B_pts else (1-v)))
auc_int=roc_auc_score(y,score)
print(f"\nINTEGER SCORE: {len(top)} features, point range {int(score.min())}-{int(score.max())}, AUROC={auc_int:.3f}")
q=pd.qcut(score,4,labels=['Low','Mod','High','VeryHigh'],duplicates='drop')
print("Risk categories (mortality):")
for cat in q.categories: print(f"   {cat:>9}: {y[q==cat].mean():.1%}  (n={ (q==cat).sum() })")
