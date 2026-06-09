import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
np.random.seed(42)

# ---------------- DeLong test (fast) for two correlated ROC AUCs -------------
def _midrank(x):
    J=np.argsort(x); Z=x[J]; N=len(x); T=np.zeros(N)
    i=0
    while i<N:
        j=i
        while j<N and Z[j]==Z[i]: j+=1
        T[i:j]=0.5*(i+j-1)+1
        i=j
    out=np.empty(N); out[J]=T; return out
def delong(y, p1, p2):
    y=np.asarray(y); p1=np.asarray(p1,float); p2=np.asarray(p2,float)
    pos=y==1; neg=y==0; m=pos.sum(); n=neg.sum()
    preds=np.vstack([p1,p2])
    def struct(pr):
        tx=np.array([_midrank(pr[k][pos]) for k in range(2)])
        ty=np.array([_midrank(pr[k][neg]) for k in range(2)])
        tz=np.array([_midrank(pr[k]) for k in range(2)])
        aucs=(tz[:,pos].sum(1)-m*(m+1)/2)/(m*n)
        v01=(tz[:,pos]-tx)/n; v10=1-(tz[:,neg]-ty)/m
        sx=np.cov(v01); sy=np.cov(v10)
        S=sx/m+sy/n
        return aucs, S
    aucs,S=struct(preds)
    var=S[0,0]+S[1,1]-2*S[0,1]
    from scipy import stats
    z=(aucs[0]-aucs[1])/np.sqrt(var) if var>0 else 0.0
    pval=2*stats.norm.sf(abs(z))
    return aucs[0],aucs[1],pval

def auc_ci(y,p,B=2000):
    rng=np.random.default_rng(42); n=len(y); a=[]; y=np.asarray(y); p=np.asarray(p)
    for _ in range(B):
        i=rng.integers(0,n,n)
        if y[i].sum() in (0,len(i)): continue
        a.append(roc_auc_score(y[i],p[i]))
    return np.percentile(a,2.5),np.percentile(a,97.5)

# ---------------- frozen pipeline (train MIMIC, apply eICU) -------------------
class Frozen:
    def __init__(self,cols): self.cols=cols
    def fit(self,df,y):
        X=df[self.cols].astype(float).copy(); self.lo=X.quantile(.01); self.hi=X.quantile(.99)
        X=X.clip(self.lo,self.hi,axis=1); self.imp=SimpleImputer(strategy='median').fit(X)
        Xi=self.imp.transform(X); self.sc=StandardScaler().fit(Xi)
        self.lr=LogisticRegression(max_iter=800,C=0.5).fit(self.sc.transform(Xi),y); return self
    def proba(self,df):
        X=df[self.cols].astype(float).copy().clip(self.lo,self.hi,axis=1)
        return self.lr.predict_proba(self.sc.transform(self.imp.transform(X)))[:,1]

# ---------------- data -------------------------------------------------------
mim=pd.read_csv('/tmp/mimic_variants.csv').rename(columns={'uo_rate_mlkghr':'uo'})   # AG + common
mr =pd.read_csv('/tmp/feat_mr.csv').rename(columns={'uo_rate_mlkghr':'uo'})          # full MIMIC most-recent (CS-MORT-8 orig vars)
eic=pd.read_csv('/tmp/eicu.csv').rename(columns={'uo_rate_mlkghr':'uo'})
cmp=pd.read_csv('/tmp/eicu_cmp.csv')
e=eic.merge(cmp,on='patientunitstayid',how='left')
ye=e['hosp_mort'].astype(int).values
ym_mim=mim['in_hospital_mortality'].astype(int).values   # labels for the mimic_variants frame (AG model)
ym_mr =mr['in_hospital_mortality'].astype(int).values    # labels for the feat_mr frame (OLD + lactate model)
COMMON=['uo','ohca_arrest','age','bun','rdw','bilirubin']

# CS-MORT-7-AG and CS-MORT-7-lactate frozen risk in eICU
ag=Frozen(['aniongap']+COMMON).fit(mim,ym_mim)
e['p_ag']=ag.proba(e)
lacm=Frozen(['lactate']+COMMON).fit(mim,ym_mim)
e['p_lac']=lacm.proba(e)

# BOS,MA2 checklist (0-6), worst-value components
def bosma2(row):
    comps=[row['bun_max']>=25, row['spo2_min']<88, row['sbp_min']<80,
           row['mech_vent']==1, row['age']>=60, row['aniongap_max']>=14]
    if any(pd.isna(x) for x in [row['bun_max'],row['spo2_min'],row['sbp_min'],row['age'],row['aniongap_max']]):
        return np.nan   # mech_vent always defined; others must be present
    return int(sum(bool(c) for c in comps))
e['bosma2']=e.apply(bosma2,axis=1)

# CS-MORT-8 ORIGINAL (8 vars) frozen on MIMIC most-recent, applied to eICU
OLD=['lactate','uo','age','bun','invasive_vent_24h','ami_cs','pressor_count','hemoglobin']
# harmonize eICU column names to MIMIC OLD vars
e8=e.rename(columns={'mech_vent':'invasive_vent_24h','ami_cs':'ami_cs','pressor_count':'pressor_count',
                     'hemoglobin_min':'hemoglobin','lactate':'lactate','bun':'bun'})
old=Frozen(OLD).fit(mr,ym_mr)
e['p_old']=old.proba(e8)

print("="*78)
print("eICU HEAD-TO-HEAD — fraction scorable + discrimination (frozen models)")
print("="*78)
def line(name,score,scor_mask):
    m=scor_mask.values if hasattr(scor_mask,'values') else scor_mask
    yy=ye[m]; ss=np.asarray(score)[m]
    a=roc_auc_score(yy,ss); lo,hi=auc_ci(yy,ss)
    print(f"  {name:28s} scorable {m.mean():.3f} (n={m.sum():4d})  AUROC {a:.3f} (95% CI {lo:.3f}-{hi:.3f})")
line("CS-MORT-7-AG", e['p_ag'], pd.Series(np.ones(len(e),bool)))      # imputed -> 100% computable
line("CS-MORT-7 (lactate)", e['p_lac'], pd.Series(np.ones(len(e),bool)))
line("BOS,MA2 (complete checklist)", e['bosma2'].fillna(-1), e['bosma2'].notna())
line("CS-MORT-8 (original, frozen)", e['p_old'], pd.Series(np.ones(len(e),bool)))

print("\n"+"="*78)
print("PRIMARY DeLong: CS-MORT-7-AG vs BOS,MA2  (patients scorable for BOTH)")
print("="*78)
both=e['bosma2'].notna()
a1,a2,pv=delong(ye[both.values], e.loc[both,'p_ag'].values, e.loc[both,'bosma2'].values)
print(f"  n={both.sum()}, events={ye[both.values].sum()}")
print(f"  CS-MORT-7-AG AUROC {a1:.3f} | BOS,MA2 AUROC {a2:.3f} | Delta {a1-a2:+.3f} | DeLong p={pv:.4g}")

print("\n"+"="*78)
print("DeLong vs original CS-MORT-8  (all eICU, frozen, both imputed-computable)")
print("="*78)
a1,a2,pv=delong(ye, e['p_lac'].values, e['p_old'].values)
print(f"  CS-MORT-7 (lactate) {a1:.3f} | CS-MORT-8-orig {a2:.3f} | Delta {a1-a2:+.3f} | DeLong p={pv:.4g}")
a1,a2,pv=delong(ye, e['p_ag'].values, e['p_old'].values)
print(f"  CS-MORT-7-AG        {a1:.3f} | CS-MORT-8-orig {a2:.3f} | Delta {a1-a2:+.3f} | DeLong p={pv:.4g}")

print("\n"+"="*78)
print("BOS,MA2 calibration in eICU (predicted vs observed by score, original RiskSLIM risks)")
print("="*78)
RISK={0:0.005,1:0.014,2:0.039,3:0.10,4:0.235,5:0.46,6:0.702}
b=e[e['bosma2'].notna()].copy(); b['bm']=b['bosma2'].astype(int)
g=b.groupby('bm').agg(n=('hosp_mort','size'),obs=('hosp_mort','mean'))
g['orig_pred']=[RISK[i] for i in g.index]; g['abs_gap']=(g['obs']-g['orig_pred']).abs()
print(g.round(3).to_string())
N=int(g['n'].sum())
ece_bm=float((g['n']*g['abs_gap']).sum()/N)
# CS-MORT-7-AG calibration error on the SAME patients (decile-grouped predicted vs observed)
bb=b.copy(); bb['dec']=pd.qcut(bb['p_ag'],10,labels=False,duplicates='drop')
ag=bb.groupby('dec').agg(n=('hosp_mort','size'),obs=('hosp_mort','mean'),pred=('p_ag','mean'))
ece_ag=float((ag['n']*(ag['obs']-ag['pred']).abs()).sum()/ag['n'].sum())
print(f"\n  Expected calibration error (weighted mean |observed - predicted|), n={N}:")
print(f"    BOS,MA2 (original RiskSLIM risks): {ece_bm:.3f}   [paper's own validation ECE was 0.026]")
print(f"    CS-MORT-7-AG (frozen MIMIC):       {ece_ag:.3f}")

print("\n"+"="*78)
print("CardShock (LVEF-limited) + IABP-SHOCK II feasibility note")
print("="*78)
# eICU echo/LVEF availability check is reported separately; CardShock needs LVEF.
print("  IABP-SHOCK II: NOT computable in eICU (requires post-PCI TIMI flow grade). Reported as non-applicable.")
print("  CardShock: requires LVEF -> eICU structured LVEF availability = 0 (no echo module). NOT computable in eICU.")
print("  => Only BOS,MA2 and SCAI stage are externally computable comparators in eICU.")
