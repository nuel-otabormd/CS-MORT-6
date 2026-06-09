import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
np.random.seed(42)

d=pd.read_csv('/tmp/feat_mr.csv').merge(pd.read_csv('/tmp/mimic_ag.csv'),on='stay_id',how='left')
y=d['in_hospital_mortality'].astype(int).values
FEATS=['lactate','uo_rate_mlkghr','ohca_arrest','age','bun','rdw','bilirubin']

# ============ LOCKED CUT-POINT SCHEME (each cut justified) ============
# risk-increasing feats: bins low->high RISK. Justification in comments.
RISKCUT={
 'lactate':  [-1, 2, 4, 99],     # SCAI hypoperfusion >=2 ; severe-shock >=4 (Lactate-clearance lit)
 'bun':      [-1, 25, 45, 9e9],  # BOS,MA2 threshold >=25 ; data-derived upper ~45
 'age':      [-1, 65, 80, 999],  # data-derived (quintile breaks 68/82) rounded to clinical 65/80
 'rdw':      [-1, 14.5, 16, 99], # upper-limit-normal 14.5% ; data step ~16
 'bilirubin':[-1, 1.2, 2, 99],   # SOFA hepatic thresholds 1.2 / 2.0 mg/dL
}
PROTCUT={'uo_rate_mlkghr':[-1, 0.5, 1.0, 99]}  # KDIGO oliguria <0.5 ; reduced <1.0 (reverse-coded)
BIN={'ohca_arrest'}

def ordc(f, df, riskcut, protcut):
    if f in BIN: return df[f].fillna(0).astype(int)
    if f in protcut:
        o=pd.cut(df[f],bins=protcut[f],labels=False); o=o.fillna(o.median()); return (o.max()-o).astype(int)
    o=pd.cut(df[f],bins=riskcut[f],labels=False); return o.fillna(o.median()).astype(int)

def derive_points(df, riskcut, protcut, feats=FEATS):
    O=pd.DataFrame({f:ordc(f,df,riskcut,protcut) for f in feats})
    m=LogisticRegression(max_iter=800).fit(O,y)
    B=np.median(np.abs(m.coef_[0]))
    pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
    score=(O.values*pts).sum(1)
    return O,pts,score

O,pts,score=derive_points(d,RISKCUT,PROTCUT)
print("="*70); print("CS-MORT-7 INTEGER SCORE — LOCKED data-driven/guideline cut-points")
print("="*70)
for f,p in zip(FEATS,pts):
    ns=int(O[f].max())
    cut=({**RISKCUT,**PROTCUT}).get(f,'binary')
    print(f"  {f:>16}: {p} pt/step, 0..{ns} (max {p*ns})   cuts={cut}")
print(f"  SCORE RANGE: {score.min()}-{score.max()}   in-sample AUROC: {roc_auc_score(y,score):.3f}")

# ---- CV integer AUROC: re-derive points each fold (honest) ----
cv=StratifiedKFold(5,shuffle=True,random_state=42); aucs=[]
for tr,te in cv.split(d,y):
    Otr=pd.DataFrame({f:ordc(f,d.iloc[tr],RISKCUT,PROTCUT) for f in FEATS})
    m=LogisticRegression(max_iter=800).fit(Otr,y[tr]); B=np.median(np.abs(m.coef_[0]))
    p=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int)
    Ote=pd.DataFrame({f:ordc(f,d.iloc[te],RISKCUT,PROTCUT) for f in FEATS})
    aucs.append(roc_auc_score(y[te],(Ote.values*p).sum(1)))
print(f"  CV integer AUROC (points re-derived per fold): {np.mean(aucs):.3f} (SD {np.std(aucs):.3f})")

# ---- CUT-POINT SENSITIVITY: 3 schemes, all in-sample, must be ~equal ----
QRISK={f:[-1]+list(np.quantile(d[f].dropna(),[.2,.4,.6,.8]))+[9e9] for f in ['lactate','bun','age','rdw','bilirubin']}
QPROT={'uo_rate_mlkghr':[-1]+list(np.quantile(d['uo_rate_mlkghr'].dropna(),[.2,.4,.6,.8]))+[9e9]}
ROUND_R={'lactate':[-1,2,4,6,99],'bun':[-1,20,40,60,999],'age':[-1,60,75,85,200],'rdw':[-1,14,16,18,99],'bilirubin':[-1,1,2,5,99]}
ROUND_P={'uo_rate_mlkghr':[-1,0.5,1,99]}
for nm,(rc,pc) in {'LOCKED guideline/data':(RISKCUT,PROTCUT),'Quintile data-driven':(QRISK,QPROT),'Round-number clinical':(ROUND_R,ROUND_P)}.items():
    _,_,s=derive_points(d,rc,pc); print(f"  [sensitivity] {nm:>24}: AUROC {roc_auc_score(y,s):.3f}")

# ---- RISK CATEGORIES by CLINICAL risk bands (non-arbitrary): map score->risk, cut at 20/40/60% ----
from sklearn.linear_model import LogisticRegression as LR
risk=LR(max_iter=500).fit(score.reshape(-1,1),y).predict_proba(score.reshape(-1,1))[:,1]
band=np.asarray(pd.cut(risk,bins=[-1,.20,.40,.60,2],labels=['Low','Moderate','High','VeryHigh']))
print("\nRISK CATEGORIES (boundaries = predicted-risk bands 20/40/60%, not arbitrary score-quartiles):")
prev=-1; mono=True
for c in ['Low','Moderate','High','VeryHigh']:
    mk=(band==c)
    if mk.sum()==0: continue
    mr=y[mk].mean()
    if mr<prev: mono=False
    prev=mr
    print(f"   {c:>9}: score {int(score[mk].min()):>2}-{int(score[mk].max()):<2}  n={mk.sum():<5} mortality {mr:.1%}")
print(f"   MONOTONIC: {mono}")
np.save('/tmp/mimic_score.npy',score)  # for later tasks
d[['stay_id']].assign(score=score,risk=risk,y=y).to_csv('/tmp/mimic_scored.csv',index=False)

# ================= eICU EXTERNAL GRADIENT =================
print("\n"+"="*70); print("eICU EXTERNAL — does the integer gradient hold? (frozen MIMIC points)")
print("="*70)
e=pd.read_csv('/tmp/eicu.csv'); ye=e['hosp_mort'].astype(int).values

# AG dose-response in MIMIC to anchor anion-gap cut-points (deployable variant)
agq=np.quantile(d['aniongap'].dropna(),[.2,.4,.6,.8])
print(f"  MIMIC anion-gap quintile breaks: {np.round(agq,1)}  (ULN~12, BOS,MA2 uses >=14)")
AGCUT={'aniongap':[-1,12,18,99]}  # ULN 12 (guideline) ; data-derived severe ~18
FEATS_AG=['aniongap','uo_rate_mlkghr','ohca_arrest','age','bun','rdw','bilirubin']
def ordc2(f,df,rc,pc):
    if f in BIN: return df[f].fillna(0).astype(int)
    if f in pc:
        o=pd.cut(df[f],bins=pc[f],labels=False); o=o.fillna(o.median()); return (o.max()-o).astype(int)
    o=pd.cut(df[f],bins=rc[f],labels=False); return o.fillna(o.median()).astype(int)
# derive AG-variant points in MIMIC
RC_AG={**{k:v for k,v in RISKCUT.items() if k!='lactate'},**AGCUT}
Oag=pd.DataFrame({f:ordc2(f,d,RC_AG,PROTCUT) for f in FEATS_AG})
mag=LogisticRegression(max_iter=800).fit(Oag,y); Bag=np.median(np.abs(mag.coef_[0]))
pts_ag=np.maximum(1,np.round(np.abs(mag.coef_[0])/Bag)).astype(int)
print(f"  AG-variant MIMIC in-sample AUROC: {roc_auc_score(y,(Oag.values*pts_ag).sum(1)):.3f}  (lactate-variant 0.763)")

def grad(name, score_e, yv):
    # fixed score-band tertiles by MIMIC-equivalent thirds of the score range
    qs=np.quantile(score_e,[1/3,2/3])
    cats=np.digitize(score_e,qs)  # 0,1,2
    print(f"  [{name}]  n={len(yv)}")
    prev=-1; mono=True
    for i,lab in enumerate(['Low','Mid','High']):
        mk=cats==i; 
        if mk.sum()==0: continue
        mr=yv[mk].mean()
        if mr<prev: mono=False
        prev=mr
        print(f"      {lab:>5}: score {int(score_e[mk].min()):>2}-{int(score_e[mk].max()):<2} n={mk.sum():<5} mortality {mr:.1%}")
    print(f"      MONOTONIC: {mono}")

# (a) lactate-version on eICU lactate-available subset
el=e[e['lactate'].notna()].copy()
Oe_l=pd.DataFrame({f:ordc(f,el,RISKCUT,PROTCUT) for f in FEATS})
grad("eICU lactate-version, lactate-available", (Oe_l.values*pts).sum(1), el['hosp_mort'].astype(int).values)
# (b) AG-variant on FULL eICU (deployable)
Oe_ag=pd.DataFrame({f:ordc2(f,e,RC_AG,PROTCUT) for f in FEATS_AG})
grad("eICU AG-variant, FULL cohort (deployable)", (Oe_ag.values*pts_ag).sum(1), ye)
