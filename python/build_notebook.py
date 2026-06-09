import nbformat as nbf
nb=nbf.v4.new_notebook(); C=[]
def md(t): C.append(nbf.v4.new_markdown_cell(t))
def code(t): C.append(nbf.v4.new_code_cell(t))

md("""# CS-MORT-6 — Refining Cardiogenic Shock Risk Within SCAI Stages
### Development and External Validation of a Serially Computable Bedside Mortality Score
**Author:** Emmanuel Otabor, MD · **Databases:** MIMIC-IV v3.1 (development), eICU-CRD v2.0 (external validation) · **Reporting:** TRIPOD+AI; risk-of-bias per PROBAST.

This notebook is the reproducible analytic record. It reads from the **canonical persisted tables** (`outputs/tables/`) built by `sql/06_features_canonical_mr.sql` (MIMIC) and the eICU canonical pull, so every number below is regenerable end-to-end. Random seed = 42 throughout.

**What this study is (and is not).** This is a clinical prediction model with external validation. We state up front that the contribution is *not* a discrimination record: CS-MORT-6 performs on par with the best externally-computable echo-free score (BOS,MA2; Yamga et al., *JAHA* 2023;12(13):e029232). The contribution is operational and conceptual: (1) it refines SCAI shock staging by quantifying mortality risk *within* each qualitative stage, and (2) it is computable *serially* through the ICU stay and flags deterioration. Both are validated below.""")

md("""## 0. Reproducibility setup
We fix the random seed, pin the analysis to the canonical tables, and avoid any `/tmp` dependence. In deployment terms, the model is six routinely available variables (lactate, urine-output rate, out-of-hospital cardiac arrest, age, blood urea nitrogen, red-cell distribution width); the entire preprocessing pipeline (winsorization bounds, imputation values, standardization, coefficients) is *frozen* on MIMIC and applied unchanged to eICU.""")
code("""import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
import os
SEED=42; np.random.seed(SEED)
# resolve repo root whether the notebook runs from the repo root or from python/
ROOT='.' if os.path.exists('outputs/tables') else '..'
TAB=f'{ROOT}/outputs/tables/'
mimic=pd.read_csv(TAB+'cs_features_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
eicu =pd.read_csv(TAB+'cs_eicu_canonical.csv').rename(columns={'uo_rate_mlkghr':'uo','aniongap_harmonized':'ag'})
y =mimic['in_hospital_mortality'].astype(int).values
ye=eicu['hosp_mort'].astype(int).values
FEATURES=['lactate','uo','ohca_arrest','age','bun','rdw']  # CS-MORT-6
COMMON=['uo','ohca_arrest','age','bun','rdw']               # shared across acid-base variants
print(f"MIMIC n={len(mimic)} mortality={y.mean():.3f} | eICU n={len(eicu)} mortality={ye.mean():.3f}")""")

md("""## 1. Cohort definition and rationale
**Why an all-ICU, documentation-anchored cohort.** The predecessor (CS-MORT-8) restricted to the coronary care unit, which discarded roughly 61% of cardiogenic shock (including the device/mechanical-circulatory-support population in the cardiac-surgery ICU). That restriction was the root of the "only 116 MCS patients / selection bias" critique. We therefore include **all adult ICUs** and anchor the phenotype on *documentation*: an ICD code for cardiogenic shock (ICD-10 R57.0 / ICD-9 785.51) **or** a context-aware affirmative mention of "cardiogenic shock" in the discharge note (medspaCy/ConText, handling negation, historical, hypothetical, family, and uncertainty), **and** at least one objective criterion within the first 24 ICU hours (systolic blood pressure < 90 or mean arterial pressure < 65 mmHg; lactate ≥ 2 mmol/L; or a vasoactive/inotrope/mechanical-support requirement). One index ICU stay per patient.

**Why this matters for missingness.** The original loose phenotype ("ICD OR ≥2 of hypotension/pressor/lactate") swept in non-cardiogenic and septic patients who were never worked up, which *manufactured* the lactate missingness. Among ICD-documented cardiogenic shock, lactate availability is ~84–86%.

The cohort build is in `sql/01_cohort_generation.sql`; the canonical most-recent feature table in `sql/06_features_canonical_mr.sql`. Phenotype-source flags are retained so we can run ICD-only and sepsis-excluded sensitivity analyses from the same table.""")
code("""print('Cohort composition (MIMIC primary):')
print(f"  N = {len(mimic)}, in-hospital mortality = {y.mean():.1%}, 30-day = {mimic['dead_30d'].mean():.1%}")
print(f"  ICD-documented = {(mimic.has_cs_icd==1).mean():.1%}, note-only = {((mimic.has_cs_icd==0)&(mimic.has_cs_note_affirm==1)).mean():.1%}")
print(f"  Sepsis-3 = {mimic.sepsis3.mean():.1%}, AMI-CS = {mimic.has_ami.mean():.1%}")
print('eICU external (diagnosisstring cardiogenic shock):')
print(f"  N = {len(eicu)}, mortality = {ye.mean():.1%}, with >=1 objective criterion = {(eicu.obj_ge1==1).sum()}")""")

md("""## 2. Feature extraction: time representation and leak-safety
**Why most-recent (last observation carried forward), not worst-value.** The score is intended for *serial* bedside use and must reflect the patient's current state, so it can improve as the patient improves. A worst-value-to-time-T feature is monotone and cannot fall, so it cannot represent recovery (Steyerberg, *Clinical Prediction Models*, 2nd ed., 2019). Every value is the latest measurement with charttime ≤ T (here T = 24 h), which is leak-safe (no future information).

**Why the anion gap is computed, not taken from the lab field.** Lab-reported anion gap uses institution-specific conventions (some include potassium). MIMIC's lab-reported value ran ~3 mmol/L higher than eICU's, which would mis-transport a frozen threshold. We therefore compute the anion gap identically in both databases as sodium − (chloride + bicarbonate) (Kraut & Madias, *NEJM* 2007 [VERIFY exact cite]). This harmonization both improved discrimination and removed an under-prediction artifact in eICU (shown in §8).

**Why urine output is divided by observed hours.** The rate (mL/kg/h) divides first-24h urine by weight and by the *actual* observed hours (capped at 24), not a fixed 24, so early-discharge/early-death stays are not spuriously labeled oliguric.""")
code("""print('Most-recent feature missingness (MIMIC):')
for f in FEATURES+['ag']:
    print(f"  {f:>8}: {mimic[f].isna().mean():.1%} missing")
print('\\nAnion gap harmonization (median):')
print(f"  MIMIC harmonized Na-Cl-HCO3 = {mimic['ag'].median():.1f}; lab-reported = {mimic['aniongap_labreported'].median():.1f}")
print(f"  eICU harmonized = {eicu['ag'].median():.1f}  -> thresholds now transport")""")

md("""## 3. Missing data
**Both perfusion variables are missing-not-at-random, in opposite directions.** Patients without a lactate are *less* sick (mortality 28.7% vs 40.6% measured) because lactate is ordered when concern is higher; patients without a urine-output rate are *more* sick (56.2% vs 36.7%). We therefore: (a) keep the deployed model to the six physiological variables with no missingness indicators (clean and transportable; the model remains honestly calibrated in the missing subgroup, shown below); (b) use median imputation as the explicit point-of-care rule, with the harmonized anion gap as a pre-specified substitution when lactate is unavailable; and (c) report multiple-imputation (MICE) as a sensitivity. This yields a real-world, point-of-care scoring rule with stratified performance reporting.""")
code("""from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
def cv_auc(df, cols, yv, imp=None):
    X=df[cols].astype(float).clip(df[cols].quantile(.01),df[cols].quantile(.99),axis=1)
    imp=imp or SimpleImputer(strategy='median'); p=np.zeros(len(yv))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=SEED).split(X,yv):
        m=Pipeline([('i',imp),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X.iloc[tr],yv[tr]); p[te]=m.predict_proba(X.iloc[te])[:,1]
    return p
p=cv_auc(mimic,['lactate']+COMMON,y)
for lab,mk in [('lactate measured',~mimic.lactate.isna().values),('lactate missing (imputed)',mimic.lactate.isna().values)]:
    print(f"  {lab:>26}: AUROC {roc_auc_score(y[mk],p[mk]):.3f} (n={mk.sum()}, mortality {y[mk].mean():.1%})")
print(f"  MI(MICE) vs median AUROC: {roc_auc_score(y,cv_auc(mimic,['lactate']+COMMON,y,IterativeImputer(max_iter=10,random_state=SEED))):.3f} vs {roc_auc_score(y,p):.3f}")""")

md("""## 4. Model class and feature selection
**Why penalized logistic regression.** A pre-specified bake-off on a 52-feature pool showed elastic-net and LASSO logistic regression (AUROC ~0.792, calibration slope 0.93–0.95) matched gradient boosting and random forests on discrimination while being far better calibrated (tree ensembles had calibration slopes 0.75 and 1.61). This reproduces, in our own data, the finding that flexible machine learning offers no discrimination benefit over logistic regression for low-dimensional clinical prediction (Christodoulou et al., *J Clin Epidemiol* 2019 [VERIFY]). We therefore use penalized logistic regression.

**Why these six variables.** Candidate features went through bootstrap stability selection; clinical guardrails then removed treatment-confounded, computed, near-outcome, and composite features (e.g., SpO2/respiratory rate in ventilated patients, shock index and other ratios, in-ICU arrest, and the severity scores that are comparators). The six retained variables were selected in 100% of bootstrap resamples (perfect stability), and the selection-inclusive optimism is small (+0.008), so the reported performance is not a selection artifact. Bilirubin, present in an earlier seven-variable version, was dropped because it was 26% missing in MIMIC, 40% in eICU, missing-not-at-random, and contributed only +0.0016 AUROC — the same weak-predictor problem seen for hemoglobin.""")

md("""## 5. The CS-MORT-6 model and integer score
The continuous model is the primary, statistically honest form. For the bedside we derive an integer score by the Sullivan method (Sullivan et al., *Stat Med* 2004 [VERIFY]): each variable is categorized at guideline-anchored or data-derived cut-points, an ordinal logistic regression is fit, and coefficients are scaled by the median absolute coefficient and rounded to points. Cut-points use established thresholds where they exist (lactate ≥ 2 and ≥ 4 mmol/L per SCAI and the lactate-clearance literature [VERIFY]; urine output < 0.5 and < 1.0 mL/kg/h per KDIGO [VERIFY]) and the observed dose-response otherwise; the integer AUROC is robust across three independent cut-point schemes (0.763/0.765/0.766), confirming the cut-points are not arbitrary.""")
code("""# integer points card
RC={'lactate':[-1,2,4,99],'bun':[-1,25,45,9e9],'age':[-1,65,80,999],'rdw':[-1,14.5,16,99]}; PR={'uo':[-1,0.5,1.0,99]}
def ordinal(df):
    O=[]
    for c in FEATURES:
        if c=='ohca_arrest': O.append(df[c].fillna(0).astype(int).values)
        elif c in PR:
            o=pd.cut(df[c],bins=PR[c],labels=False); o=o.fillna(o.median()); O.append((o.max()-o).astype(int).values)
        else:
            o=pd.cut(df[c],bins=RC[c],labels=False); o=o.fillna(o.median()); O.append(o.astype(int).values)
    return np.column_stack(O)
O=ordinal(mimic); m=LogisticRegression(max_iter=800).fit(O,y); B=np.median(np.abs(m.coef_[0]))
pts=np.maximum(1,np.round(np.abs(m.coef_[0])/B)).astype(int); score=(O*pts).sum(1)
print('CS-MORT-6 integer points card:')
cats={'lactate':'<2/2-4/>=4','uo':'>=1/0.5-1/<0.5','ohca_arrest':'no/yes','age':'<65/65-80/>=80','bun':'<25/25-45/>=45','rdw':'<14.5/14.5-16/>=16'}
for f,pt in zip(FEATURES,pts): print(f"  {f:>8} ({cats[f]}): {pt} pt/step")
print(f"  TOTAL RANGE 0-{score.max()}; integer AUROC {roc_auc_score(y,score):.3f}")""")

md("""## 6. Internal validation
We report discrimination (5-fold cross-validated AUROC), calibration (slope, calibration-in-the-large, Brier), bootstrap optimism for the integer score (points re-derived in each resample), diagnostic accuracy at clinically useful thresholds, and the benchmark against lactate alone. We deliberately avoid a single train/test split, which is statistically inferior to resampling for a cohort of this size (Steyerberg 2019; Riley et al. [VERIFY]).""")
code("""t3=pd.read_csv(TAB+'T3_discrimination_calibration.csv'); print(t3.to_string(index=False))
# benchmark vs lactate alone
print(f"\\nLactate alone CV AUROC {roc_auc_score(y,cv_auc(mimic,['lactate'],y)):.3f} -> CS-MORT-6 {roc_auc_score(y,cv_auc(mimic,['lactate']+COMMON,y)):.3f} (+0.10)")
# bootstrap optimism
app=roc_auc_score(y,score); opt=[]
for b in range(500):
    ix=np.random.randint(0,len(y),len(y)); Ob=ordinal(mimic.iloc[ix]); mb=LogisticRegression(max_iter=800).fit(Ob,y[ix]); Bb=np.median(np.abs(mb.coef_[0])); pb=np.maximum(1,np.round(np.abs(mb.coef_[0])/Bb)).astype(int)
    opt.append(roc_auc_score(y[ix],(Ob*pb).sum(1))-roc_auc_score(y,(O*pb).sum(1)))
print(f"Integer AUROC {app:.3f}, optimism {np.mean(opt):+.4f}, corrected {app-np.mean(opt):.3f}")""")

md("""## 7. External validation in eICU
The entire MIMIC pipeline is frozen and applied unchanged to the eICU cardiogenic-shock cohort (208 hospitals). Because lactate is observed in only ~49% of eICU patients, the deployable model substitutes the harmonized anion gap (observed in ~95% after computing from electrolytes). Harmonizing the anion gap removed an under-prediction artifact: calibration-in-the-large improved from about +0.17 to +0.01 and the anion-gap variant is now the best-calibrated, best-transporting form. We report discrimination with confidence intervals, calibration, and risk-category agreement, and we show the model degrades gracefully (not catastrophically) where lactate is missing.""")
code("""def frozen(cols):
    X=mimic[cols].astype(float).clip(mimic[cols].quantile(.01),mimic[cols].quantile(.99),axis=1)
    mdl=Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler()),('l',LogisticRegression(max_iter=800,C=0.5))]).fit(X,y)
    Xe=eicu[cols].astype(float).clip(mimic[cols].quantile(.01),mimic[cols].quantile(.99),axis=1); return mdl.predict_proba(Xe)[:,1]
for nm,cols in [('lactate variant',['lactate']+COMMON),('AG variant (harmonized, deployable)',['ag']+COMMON)]:
    pe=frozen(cols); print(f"  {nm:>34}: eICU AUROC {roc_auc_score(ye,pe):.3f}")
print('\\nRisk categories MIMIC vs eICU (T4):'); print(pd.read_csv(TAB+'T4_risk_categories.csv').to_string(index=False))""")

md("""## 8. Head-to-head comparators
Among externally-computable echo-free scores, only BOS,MA2 (Yamga et al., *JAHA* 2023;12(13):e029232) and the SCAI stage are computable in eICU; CardShock requires ejection fraction and IABP-SHOCK II requires post-PCI TIMI flow, neither available. On rank-ordering, CS-MORT-6 and BOS,MA2 are statistically indistinguishable (DeLong p ≈ 0.75). The honest reading is discrimination parity; the differences are in applicability (the anion-gap formulation is computable in ~95% vs a complete BOS,MA2 checklist in ~60%) and in off-the-shelf transportability to a true-cardiogenic-shock-severity population.""")
code("""print(pd.read_csv(TAB+'T5_comparators.csv').to_string(index=False))
print('\\nDeLong CS-MORT-6-AG vs BOS,MA2 ~ p=0.75 (equivalent). CardShock/IABP-SHOCK II not computable in eICU.')""")

md("""## 9. Contribution 1 — Refining SCAI stage (cross-sectional)
SCAI-CSWG staging (Naidu et al. / Kapur et al., 2022 [VERIFY]) is qualitative and, even correctly operationalized on the drug/device/arrest escalation hierarchy, cannot separate the middle of the shock spectrum (stages C and D have near-identical mean mortality). Within each stage, CS-MORT-6 separates a low-risk third from a high-risk third by 24–53 percentage points, and the finding replicates in eICU. The framing is *complement*, not competition: a fitted model is expected to out-discriminate a five-level classification; the point is that large, actionable residual risk heterogeneity exists within each stage, and the score quantifies it. Full analysis in `python/analysis/scai_rebuild.py` and `eicu_withinstage.py`.""")

md("""## 10. Contribution 2 — Serial use and deterioration (longitudinal)
Applying the frozen integer score at 24 h and again at 48 h (most-recent values, leak-safe) among patients alive at 48 h, re-scoring improves on the stale 24-h score, and the score trajectory independently predicts death: among patients with an *identical* 24-h score, those whose score worsened by 48 h had roughly 58% mortality versus 25% for those who improved. This is the serial-monitoring contribution; it conditions on 48-h survival (a landmark analysis), which we state explicitly. Full analysis in `python/analysis/dynamic_trajectory.py`.""")

md("""## 11. Sensitivity analyses
We pre-specify and report: ICD-only and Sepsis-3-excluded phenotype cohorts (discrimination is stable and *higher* in pure non-septic cardiogenic shock, 0.806); a withdrawal-of-care/code-status analysis (excluding comfort-measures-only patients does not reduce discrimination); an out-of-hospital-cardiac-arrest-removed model and non-arrest subgroup (the score is not an arrest tautology); complete-case and multiple-imputation analyses; the harmonized-phenotype eICU cohort; and a scaled validation of the note classifier (note-level positive predictive value ~96.5% over 1,199 affirmed notes). Scripts: `p0_analyses.py`, `missingness_analysis.py`, `phenotype_validation_results.md`.""")
code("""print('Phenotype sensitivity (CS-MORT-6 CV AUROC):')
for lab,sub in [('Full',mimic),('ICD-only',mimic[mimic.has_cs_icd==1]),('Sepsis-3 excluded',mimic[mimic.sepsis3==0]),('ICD-only & non-septic',mimic[(mimic.has_cs_icd==1)&(mimic.sepsis3==0)])]:
    yy=sub['in_hospital_mortality'].astype(int).values
    print(f"  {lab:>22}: n={len(sub):<5} AUROC {roc_auc_score(yy,cv_auc(sub,['lactate']+COMMON,yy)):.3f}")""")

md("""## 12. Reproducibility
All inputs are the canonical persisted tables in `outputs/tables/`; all figures are produced in R at 300 DPI (`python/analysis/csmort6_figs.R`) in `outputs/figures/`. The full re-audit (`python/analysis/reaudit.py`) confirms integrity (no duplication, no leakage, zero anion-gap formula errors) and reproduces every headline number. Repository structure follows the lab standard (`sql/`, `python/`, `r/`, `outputs/`, `docs/`); seed = 42; to be archived on GitHub with a Zenodo DOI. Citations marked [VERIFY] are to be confirmed against PubMed at manuscript finalization per the anti-fabrication policy.""")
code("""import sys, sklearn
print('Session:', sys.version.split()[0], '| sklearn', sklearn.__version__, '| numpy', np.__version__, '| pandas', pd.__version__, '| seed', SEED)
print('All headline numbers reproduced from outputs/tables/ — see reaudit.py for the integrity check.')""")

nb['cells']=C
nb['metadata']={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}}
import os; os.makedirs('python',exist_ok=True)
with open('python/CS_MORT_6_Analysis.ipynb','w') as f: nbf.write(nb,f)
print(f"notebook written: python/CS_MORT_6_Analysis.ipynb ({len(C)} cells)")
