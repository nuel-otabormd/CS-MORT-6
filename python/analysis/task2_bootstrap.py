import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
np.random.seed(2026)
d=pd.read_csv('/tmp/feat_mr.csv').merge(pd.read_csv('/tmp/mimic_ag.csv'),on='stay_id',how='left')
y=d['in_hospital_mortality'].astype(int).values; N=len(y)
FEATS=['lactate','uo_rate_mlkghr','ohca_arrest','age','bun','rdw','bilirubin']
RISKCUT={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99],'bilirubin':[-1,1.2,2,99]}
PROTCUT={'uo_rate_mlkghr':[-1,0.5,1.0,99]}; BIN={'ohca_arrest'}
def ordframe(df):
    cols={}
    for f in FEATS:
        if f in BIN: cols[f]=df[f].fillna(0).astype(int).values
        elif f in PROTCUT:
            o=pd.cut(df[f],bins=PROTCUT[f],labels=False); o=o.fillna(o.median()); cols[f]=(o.max()-o).astype(int).values
        else:
            o=pd.cut(df[f],bins=RISKCUT[f],labels=False); cols[f]=o.fillna(o.median()).astype(int).values
    return np.column_stack([cols[f] for f in FEATS])
def fitpoints(O,yy):
    m=LogisticRegression(max_iter=800).fit(O,yy); B=np.median(np.abs(m.coef_[0]))
    return np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
O=ordframe(d); pts=fitpoints(O,y); score=(O*pts).sum(1)
C_app=roc_auc_score(y,score)
# ---- Steyerberg/Harrell bootstrap optimism (re-derive points each boot) ----
B=500; opt=[]
for b in range(B):
    idx=np.random.randint(0,N,N)
    Ob=O[idx]; yb=y[idx]
    pb=fitpoints(Ob,yb)
    c_boot=roc_auc_score(yb,(Ob*pb).sum(1))         # apparent in bootstrap
    c_orig=roc_auc_score(y,(O*pb).sum(1))           # bootstrap model on original
    opt.append(c_boot-c_orig)
opt=np.array(opt); optimism=opt.mean()
print("="*64); print("BOOTSTRAP OPTIMISM CORRECTION (integer score, B=500)")
print("="*64)
print(f"  Apparent AUROC          : {C_app:.4f}")
print(f"  Optimism (mean)         : {optimism:.4f}  (95% {np.percentile(opt,2.5):.4f} to {np.percentile(opt,97.5):.4f})")
print(f"  Optimism-corrected AUROC: {C_app-optimism:.4f}")
# ---- Diagnostic accuracy at score thresholds ----
print("\n"+"="*64); print("DIAGNOSTIC ACCURACY at score thresholds (predict death if score>=t)")
print("="*64)
P=y.sum(); Ng=N-P
print(f"  {'thr':>3} {'n>=t':>5} {'sens':>5} {'spec':>5} {'PPV':>5} {'NPV':>5} {'LR+':>5} {'LR-':>5}")
for t in [4,5,6,7,8,9,10]:
    pred=score>=t; tp=(pred&(y==1)).sum(); fp=(pred&(y==0)).sum()
    fn=(~pred&(y==1)).sum(); tn=(~pred&(y==0)).sum()
    sens=tp/P; spec=tn/Ng; ppv=tp/max(tp+fp,1); npv=tn/max(tn+fn,1)
    lrp=sens/max(1-spec,1e-9); lrn=(1-sens)/max(spec,1e-9)
    print(f"  {t:>3} {pred.sum():>5} {sens:>5.2f} {spec:>5.2f} {ppv:>5.2f} {npv:>5.2f} {lrp:>5.2f} {lrn:>5.2f}")
# ---- Score -> observed mortality (calibration of the integer scale) ----
print("\n"+"="*64); print("SCORE -> OBSERVED MORTALITY (integer-scale calibration)")
print("="*64)
sd=pd.DataFrame({'s':score,'y':y})
g=sd.groupby('s').agg(n=('y','size'),deaths=('y','sum'),mort=('y','mean'))
g['mort']=(g['mort']*100).round(1)
print(g.to_string())
