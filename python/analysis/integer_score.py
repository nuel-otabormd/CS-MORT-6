import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler, SplineTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
np.random.seed(42)

d=pd.read_csv('/tmp/feat_mr.csv').rename(columns={'uo_rate_mlkghr':'uo'})
y=d['in_hospital_mortality'].astype(int).values
CONT=['lactate','uo','age','bun','rdw','bilirubin']; BIN=['ohca_arrest']
cv=StratifiedKFold(5,shuffle=True,random_state=42)

# ============================================================================
# 1. PRIMARY (statistically honest) = restricted cubic spline logistic model
# ============================================================================
def spline_auc():
    X=d[CONT].astype(float).copy()
    for c in CONT: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    pre=make_pipeline(SimpleImputer(strategy='median'),
                      SplineTransformer(degree=3,n_knots=4,include_bias=False))
    Xs=pre.fit_transform(X)
    Xs=np.column_stack([Xs, d[BIN].fillna(0).values])
    p=cross_val_predict(LogisticRegression(max_iter=2000,C=1.0),StandardScaler().fit_transform(Xs),y,cv=cv,method='predict_proba')[:,1]
    return roc_auc_score(y,p)
auc_spline=spline_auc()

# linear (non-spline) continuous reference
def lin_auc():
    X=d[CONT+BIN].astype(float).copy()
    for c in CONT: lo,hi=X[c].quantile(.01),X[c].quantile(.99); X[c]=X[c].clip(lo,hi)
    p=cross_val_predict(make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(max_iter=800,C=0.5)),X,y,cv=cv,method='predict_proba')[:,1]
    return roc_auc_score(y,p)
auc_linear=lin_auc()

# ============================================================================
# 2. CUT-POINT SCHEMES  (ordinal level per variable)
# ============================================================================
def ordinal(col, edges, protective=False):
    """Return ordinal level 0..len(edges) by how many ascending thresholds are crossed.
       protective=True => low values are bad (reverse)."""
    v=d[col].astype(float)
    lvl=np.zeros(len(v))
    for e in edges: lvl=lvl+(v>=e).astype(float)
    if protective:  # low is bad: count descending thresholds crossed
        lvl=np.zeros(len(v))
        for e in edges: lvl=lvl+(v<e).astype(float)
    s=pd.Series(lvl,index=d.index); s[v.isna()]=np.nan
    return s

# (B) CLINICAL / guideline-anchored cut-points (justified by dose-response + guidelines)
CLIN={
 'lactate':   dict(edges=[2,4],        protective=False),   # SCAI >=2 / >=4
 'uo':        dict(edges=[1.0,0.5,0.3],protective=True),    # KDIGO <1/<0.5/<0.3  (low=bad)
 'age':       dict(edges=[60,75,85],   protective=False),   # geriatric strata
 'bun':       dict(edges=[20,40,60],   protective=False),   # uremia (data edges 19/39/58)
 'rdw':       dict(edges=[14.5,16,18], protective=False),   # normal upper 14.5 (data inflection)
 'bilirubin': dict(edges=[1.2,2],      protective=False),   # normal <1.2; signal >1.7
}
# (A) DATA quintile cut-points (rounded to the observed quintile edges)
QUINT={
 'lactate':   dict(edges=[1.3,1.7,2.4,4.0], protective=False),
 'uo':        dict(edges=[1.406,0.844,0.52,0.244], protective=True),
 'age':       dict(edges=[59,68,75,82], protective=False),
 'bun':       dict(edges=[19,28,39,58], protective=False),
 'rdw':       dict(edges=[13.8,14.6,15.9,17.6], protective=False),
 'bilirubin': dict(edges=[0.4,0.7,1.0,1.7], protective=False),
}
# (C) SPLINE-inflection cut-points (where the spline risk accelerates; read off dose-response)
SPLINE={
 'lactate':   dict(edges=[2,4],        protective=False),
 'uo':        dict(edges=[0.5,0.25],   protective=True),
 'age':       dict(edges=[65,80],      protective=False),
 'bun':       dict(edges=[30,55],      protective=False),
 'rdw':       dict(edges=[14.5,17.5],  protective=False),
 'bilirubin': dict(edges=[1.7],        protective=False),
}

def build_points(scheme):
    """Sullivan-style: ordinal-code each var, fit multivariable LR on ordinal levels,
       points per one-level step = round(beta / reference beta). Returns (points_dict, score_vector)."""
    O=pd.DataFrame({c:ordinal(c,**scheme[c]) for c in scheme})
    O['ohca_arrest']=d['ohca_arrest'].fillna(0).astype(float)
    Oi=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(O),columns=O.columns)
    lr=LogisticRegression(max_iter=800).fit(Oi,y)             # raw (unstandardized) per-level betas
    beta=dict(zip(O.columns,lr.coef_[0]))
    ref=np.median([b for b in beta.values() if b>0])          # reference unit
    pts={k:max(1,int(round(b/ref))) if b>0 else 0 for k,b in beta.items()}
    score=sum(Oi[k]*pts[k] for k in O.columns)
    return pts, score.values, beta

def cv_auc_score(scoremaker):
    """5-fold CV: rebuild points on train fold, score test fold."""
    aucs=[]
    for tr,te in cv.split(d,y):
        # rebuild ordinal+points on FULL data points scheme but refit beta on train
        pass
    # simpler: scores are monotone transform of a fixed linear combo; CV the LR on ordinal levels
    return None

print("="*76)
print("CS-MORT-7 INTEGER SCORE — cut-point derivation & robustness")
print("="*76)
print(f"\nPRIMARY continuous models (5-fold CV AUROC):")
print(f"   restricted cubic spline : {auc_spline:.3f}   <- statistically honest primary")
print(f"   linear logistic         : {auc_linear:.3f}")

print(f"\nINTEGER score AUROC under 3 cut-point schemes (in-sample, same point method):")
schemes={'DATA quintile':QUINT,'CLINICAL guideline':CLIN,'SPLINE inflection':SPLINE}
for nm,sch in schemes.items():
    pts,score,beta=build_points(sch)
    a=roc_auc_score(y,score)
    print(f"   {nm:20s}: integer AUROC {a:.3f}   points={pts}")

# bootstrap optimism-corrected integer AUROC for the CLINICAL scheme
def integer_apparent_and_optimism(scheme,B=200):
    O=pd.DataFrame({c:ordinal(c,**scheme[c]) for c in scheme}); O['ohca_arrest']=d['ohca_arrest'].fillna(0).astype(float)
    Oi=pd.DataFrame(SimpleImputer(strategy='median').fit_transform(O),columns=O.columns)
    def fit_points(Xd,yy):
        lr=LogisticRegression(max_iter=800).fit(Xd,yy); beta=dict(zip(Xd.columns,lr.coef_[0]))
        ref=np.median([b for b in beta.values() if b>0]); return {k:max(1,int(round(b/ref))) if b>0 else 0 for k,b in beta.items()}
    pts0=fit_points(Oi,y); s0=sum(Oi[k]*pts0[k] for k in Oi.columns).values; app=roc_auc_score(y,s0)
    opt=[]
    rng=np.random.default_rng(42)
    for _ in range(B):
        idx=rng.integers(0,len(y),len(y))
        ptsb=fit_points(Oi.iloc[idx],y[idx])
        sb=sum(Oi[k]*ptsb[k] for k in Oi.columns)
        auc_boot=roc_auc_score(y[idx], sb.values[idx]); auc_orig=roc_auc_score(y, sb.values)
        opt.append(auc_boot-auc_orig)
    return app, app-np.mean(opt), pts0
app,corr,pts_final=integer_apparent_and_optimism(CLIN)
print(f"\nCLINICAL integer score bootstrap optimism-correction: apparent {app:.3f} -> corrected {corr:.3f}")

# ============================================================================
# 3. FINAL POINTS TABLE + RISK CATEGORIES (monotonic gradient)
# ============================================================================
pts,score,beta=build_points(CLIN)
d['score']=score
print("\n"+"="*76); print("FINAL CS-MORT-7 INTEGER POINTS (CLINICAL scheme)"); print("="*76)
LBL={'lactate':'Lactate (mmol/L): 0/<2, +p each >=2, >=4',
     'uo':'Urine output (mL/kg/h): 0/>=1, +p each <1, <0.5, <0.3',
     'age':'Age (y): 0/<60, +p each >=60, >=75, >=85',
     'bun':'BUN (mg/dL): 0/<20, +p each >=20, >=40, >=60',
     'rdw':'RDW (%): 0/<14.5, +p each >=14.5, >=16, >=18',
     'bilirubin':'Bilirubin (mg/dL): 0/<1.2, +p each >=1.2, >=2',
     'ohca_arrest':'OHCA (out-of-hosp arrest): yes'}
for k in ['lactate','uo','age','bun','rdw','bilirubin','ohca_arrest']:
    print(f"   {pts[k]} pt/level   {LBL[k]}")
print(f"   SCORE RANGE: {int(d.score.min())} to {int(d.score.max())}")

# risk categories by score bands -> choose data-driven bands giving monotone gradient
print("\nObserved mortality by integer score (monotonic dose-response):")
g=d.groupby('score').agg(n=('in_hospital_mortality','size'),mort=('in_hospital_mortality','mean'))
print(g.round(3).to_string())

# define 4 clinically-actionable categories on score quartile-ish bands
qs=d['score'].quantile([.25,.5,.75]).round().astype(int).tolist()
def cat(s):
    a,b,c=qs
    return 'Low' if s<=a else 'Intermediate' if s<=b else 'High' if s<=c else 'Very High'
d['risk_cat']=d['score'].apply(cat)
order=['Low','Intermediate','High','Very High']
gc=d.groupby('risk_cat').agg(n=('in_hospital_mortality','size'),mort=('in_hospital_mortality','mean')).reindex(order)
print(f"\nRISK CATEGORIES (score bands from quartiles {qs}):")
print(gc.round(3).to_string())
mono = all(gc['mort'].values[i] < gc['mort'].values[i+1] for i in range(3))
print(f"   Monotonic gradient (MIMIC): {mono}")

# persist the points table + bands for the eICU step
import json
json.dump({'points':pts,'scheme':'CLINICAL','bands':qs,
           'edges':{k:CLIN[k]['edges'] for k in CLIN},
           'protective':{k:CLIN[k]['protective'] for k in CLIN}},
          open('/tmp/csmort7_integer.json','w'),indent=2)
print("\n[saved /tmp/csmort7_integer.json for eICU validation]")
