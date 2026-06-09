import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, json
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
np.random.seed(42)

mr =pd.read_csv('/tmp/feat_mr.csv').rename(columns={'uo_rate_mlkghr':'uo'})       # MIMIC (lactate integer)
mim=pd.read_csv('/tmp/mimic_variants.csv').rename(columns={'uo_rate_mlkghr':'uo'}) # MIMIC (AG integer)
eic=pd.read_csv('/tmp/eicu.csv').rename(columns={'uo_rate_mlkghr':'uo'})           # eICU
ym=mr['in_hospital_mortality'].astype(int).values       # labels for the feat_mr frame (lactate integer)
ym_mim=mim['in_hospital_mortality'].astype(int).values  # labels for the mimic_variants frame (AG integer)
ye=eic['hosp_mort'].astype(int).values

def ordinal(df,col,edges,protective):
    v=df[col].astype(float); lvl=np.zeros(len(v))
    for e in edges: lvl=lvl+((v<e) if protective else (v>=e)).astype(float)
    s=pd.Series(lvl,index=df.index); s[v.isna()]=np.nan; return s

def derive_points(train, specs, ohcacol='ohca_arrest', ylab='in_hospital_mortality'):
    O=pd.DataFrame({c:ordinal(train,c,**specs[c]) for c in specs}); O[ohcacol]=train[ohcacol].fillna(0).astype(float)
    med=O.median()                       # MIMIC median ordinal level (frozen, for imputing missing externally)
    Oi=O.fillna(med)
    lr=LogisticRegression(max_iter=800).fit(Oi, train[ylab].astype(int).values)
    beta=dict(zip(O.columns,lr.coef_[0])); ref=np.median([b for b in beta.values() if b>0])
    pts={k:max(1,int(round(b/ref))) if b>0 else 0 for k,b in beta.items()}
    return pts, med.to_dict()

def score_frame(df, specs, pts, med, ohcacol='ohca_arrest'):
    O=pd.DataFrame({c:ordinal(df,c,**specs[c]) for c in specs}); O[ohcacol]=df[ohcacol].fillna(0).astype(float)
    Oi=O.fillna(pd.Series(med))           # impute missing with FROZEN MIMIC median level
    return sum(Oi[k]*pts[k] for k in O.columns).values

def cat(score, bands):
    a,b,c=bands
    return np.select([score<=a,score<=b,score<=c],['Low','Intermediate','High'],default='Very High')

def report(name, sc, yy, bands):
    df=pd.DataFrame({'s':sc,'y':yy}); df['cat']=cat(df['s'].values,bands)
    order=['Low','Intermediate','High','Very High']
    g=df.groupby('cat').agg(n=('y','size'),mort=('y','mean')).reindex(order)
    mono=all(g['mort'].values[i]<g['mort'].values[i+1] for i in range(3))
    print(f"\n  {name}: integer AUROC {roc_auc_score(yy,sc):.3f} | bands {bands} | monotonic={mono}")
    print(g.round(3).to_string())
    return g

# ---- LACTATE integer (frozen on MIMIC feat_mr) ----
LAC=json.load(open('/tmp/csmort7_integer.json'))
specs_lac={k:dict(edges=LAC['edges'][k],protective=LAC['protective'][k]) for k in LAC['edges']}
pts_lac,med_lac=derive_points(mr,specs_lac)
bands_lac=LAC['bands']
print("="*74); print("FROZEN LACTATE INTEGER applied to eICU"); print("="*74)
print(f"  points={pts_lac}  median-levels(frozen)={ {k:round(v,1) for k,v in med_lac.items()} }")
report("MIMIC (reference)", score_frame(mr,specs_lac,pts_lac,med_lac), ym, bands_lac)
report("eICU (frozen, lactate imputed where missing)", score_frame(eic,specs_lac,pts_lac,med_lac), ye, bands_lac)

# ---- ANION-GAP integer (the deployable eICU version; frozen on MIMIC mimic_variants) ----
specs_ag={
 'aniongap':  dict(edges=[12,16,20], protective=False),
 'uo':        dict(edges=[1.0,0.5,0.3], protective=True),
 'age':       dict(edges=[60,75,85], protective=False),
 'bun':       dict(edges=[20,40,60], protective=False),
 'rdw':       dict(edges=[14.5,16,18], protective=False),
 'bilirubin': dict(edges=[1.2,2], protective=False),
}
pts_ag,med_ag=derive_points(mim,specs_ag)
# choose AG-score bands from MIMIC quartiles of the AG score
s_ag_mim=score_frame(mim,specs_ag,pts_ag,med_ag)
bands_ag=list(np.quantile(s_ag_mim,[.25,.5,.75]).round().astype(int))
print("\n"+"="*74); print("FROZEN ANION-GAP INTEGER (CS-MORT-7-AG, deployable) applied to eICU"); print("="*74)
print(f"  points={pts_ag}  bands(MIMIC quartiles)={bands_ag}")
report("MIMIC (reference)", s_ag_mim, ym_mim, bands_ag)
report("eICU (frozen)", score_frame(eic,specs_ag,pts_ag,med_ag), ye, bands_ag)
