"""CS-MORT-6 historical predictor screen (archived, re-executed).

This script reproduces the historical 58-parameter stability screen that
informed the subsequent clinical selection of the CS-MORT-6 predictors. The
screen did NOT itself determine the final six-variable set: it returns 38
stable parameters, and the reduction to six was made by clinical review and
comparison of candidate subsets, which were not preserved in code.

It predates the 24-hour landmark design, runs on the pre-landmark baseline
extract, and is not part of `run_all.sh`; no reported landmark or external
result depends on it. It is here for provenance.

Method: 400 row-level bootstrap resamples of L1-penalized (lasso) logistic
regression on winsorized, median-imputed, standardized candidates; a variable
counts as stable when selected in at least 80% of resamples.

The top-k block below is DESCRIPTIVE ONLY. Predictors are ranked using
full-sample outcome information, preprocessing precedes cross-validation,
repeated ICU stays are not grouped by patient, the fits use an L2 penalty
while the screen uses L1, and 13 parameters tie at a selection frequency of
1.00 so their ordering is arbitrary. The top-six subset is not CS-MORT-6: its
six predictors sit at ranks 1, 4, 8, 10, 12 and 16, and blood urea nitrogen
appears in no subset up to twelve. These AUROCs are not out-of-sample
estimates and are not a comparison against CS-MORT-6.
"""
import warnings; warnings.filterwarnings('ignore')
import os as _os
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

_B = _os.path.dirname(_os.path.abspath(__file__))
DATA = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'
OUT  = _os.environ.get('CSMORT6_OUT',  _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
np.random.seed(42)

# excluded by design: identifiers and outcomes; composite severity scores, which
# are comparators rather than candidates; treatment-confounded clinical
# guardrails; and collinear duplicates of retained variables.
EXCLUDE = {'stay_id','subject_id','hadm_id','in_hospital_mortality','dead_30d','died_before_24h',
 'in_primary_cohort','in_core_cohort','in_documented_only','present_at_24h','present_at_48h',
 'present_at_72h','anchor_year_group','cs_etiology','non_ami_cs',
 'sofa_24h','apsiii','sapsii','oasis','charlson_comorbidity_index','scai_cswg_stage',
 'aniongap_max','spo2_min','resp_rate_max','rhy_asystole',
 'renal_disease','urineoutput_24h','alt_max','preadm_creatinine','baseexcess_min'}

b = pd.read_csv(DATA + 'feat_baseline_full.csv')
b['gender'] = (b['gender'] == 'M').astype(int)
b['nee_max'] = b['nee_max'].fillna(0)
y = b['in_hospital_mortality'].astype(int).values

feat = [c for c in b.columns if c not in EXCLUDE and b[c].dtype != 'object']
X = b[feat].astype(float)
for c in feat:
    lo, hi = X[c].quantile(.01), X[c].quantile(.99)
    X[c] = X[c].clip(lo, hi)
X['lactate_missing'] = b['lactate_max'].isna().astype(int)
feat = feat + ['lactate_missing']
Xi = pd.DataFrame(SimpleImputer(strategy='median').fit_transform(X), columns=feat)
Xs = StandardScaler().fit_transform(Xi)
print(f"screening extract: n={len(b)} ICU stays, {y.sum()} deaths, "
      f"{b['hadm_id'].nunique()} admissions, {b['subject_id'].nunique()} patients")
print(f"candidate parameters: {len(feat)}")

B = 400
cnt = np.zeros(len(feat))
for _ in range(B):
    idx = np.random.choice(len(y), len(y), replace=True)
    lr = LogisticRegression(penalty='l1', solver='liblinear', C=0.1, max_iter=500)
    cnt += (np.abs(lr.fit(Xs[idx], y[idx]).coef_[0]) > 1e-6)
stab = pd.Series(cnt / B, index=feat).sort_values(ascending=False)

print(f"\nstable set (selected in >= 80% of {B} resamples): {(stab >= 0.80).sum()} variables")
for k, v in stab[stab >= 0.80].items():
    print(f"  {v:.2f}  {k}")

cv = StratifiedKFold(5, shuffle=True, random_state=42)
print("\nparsimony (CV AUROC of the top-k stable variables):")
rows = []
for k in [6, 7, 8, 9, 10, 12, 15]:
    cols = stab.index[:k].tolist()
    a = cross_val_score(LogisticRegression(max_iter=800),
                        StandardScaler().fit_transform(Xi[cols]), y, cv=cv,
                        scoring='roc_auc').mean()
    rows.append({'top_k': k, 'cv_auroc': round(a, 4)})
    print(f"  top {k:2d}: {a:.3f}")

pd.DataFrame({'variable': stab.index, 'selection_frequency': stab.values}) \
  .to_csv(OUT + 'predictor_screen_stability.csv', index=False)
pd.DataFrame(rows).to_csv(OUT + 'predictor_screen_parsimony.csv', index=False)
print(f"\nwrote {OUT}predictor_screen_stability.csv and predictor_screen_parsimony.csv")
