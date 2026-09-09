"""Supplement table assembly.

Builds the supplementary tables from pipeline outputs and computes landmark
threshold accuracy.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
DATA    = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'
SCRATCH = DATA
OUT     = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
DOC     = _os.environ.get('CSMORT6_SUPPLEMENT', OUT + 'SUPPLEMENT_TABLES.md')

def md(df, floatfmt=None):
    df = df.copy()
    if floatfmt:
        for c in df.columns:
            if df[c].dtype.kind == 'f':
                df[c] = df[c].map(lambda v: floatfmt % v)
    header = '| ' + ' | '.join(str(c) for c in df.columns) + ' |'
    sep = '|' + '|'.join(['---'] * len(df.columns)) + '|'
    rows = ['| ' + ' | '.join(str(v) for v in r) + ' |' for r in df.values]
    return '\n'.join([header, sep] + rows)

# ---- landmark threshold table (computed inline, saved) ----
# score the landmark population with the deployed card itself (the stored
# score_v2 column is step 01's re-derivation variant, not the deployed card)
import os as _os
_gl = {'__file__': _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '05_internal_analyses.py')}
_src = open(_gl['__file__']).read()
exec(compile(_src.split('# ============ 1+2.')[0], '05_partA', 'exec'), _gl)
y = _gl['y']; s = _gl['card_score'](_gl['lm'], _gl['MED'])
rows = []
for thr in [4, 6, 8, 9]:
    pred = s >= thr
    tp = int(((pred) & (y == 1)).sum()); fp = int(((pred) & (y == 0)).sum())
    fn = int(((~pred) & (y == 1)).sum()); tn = int(((~pred) & (y == 0)).sum())
    sens = tp / (tp + fn); spec = tn / (tn + fp)
    rows.append(dict(threshold=f">= {thr}", sensitivity=f"{sens:.2f}", specificity=f"{spec:.2f}",
                     PPV=f"{tp/(tp+fp):.2f}", NPV=f"{tn/(tn+fn):.2f}",
                     LRpos=f"{sens/(1-spec):.2f}", LRneg=f"{(1-sens)/spec:.2f}"))
thr_tab = pd.DataFrame(rows)
thr_tab.to_csv(OUT + 'landmark_thresholds.csv', index=False)

spec = pd.read_csv(OUT + 'v2_spec_continuous.csv')
card = pd.read_csv(OUT + 'v2_integer_card.csv')
mapping = pd.read_csv(OUT + 'v2_score_risk_mapping.csv')
bands = pd.read_csv(OUT + 'v2_risk_bands_oof.csv')
evt = pd.read_csv(OUT + 'event_time_exact.csv')
traj = pd.read_csv(OUT + 'trajectory_symmetric.csv')
corr = pd.read_csv(OUT + 'correlation_matrix_lm24.csv', index_col=0)
fair = pd.read_csv(OUT + 'fairness_subgroups_lm24.csv')
f1m = pd.read_csv(OUT + 'figure1_mimic_lm24.csv')
f1e = pd.read_csv(OUT + 'figure1_eicu_lm24.csv')
selD = pd.read_csv(OUT + 'challenger_selection.csv')
selS = pd.read_csv(OUT + 'challenger_symmetric_selection.csv')
avail = pd.read_csv(OUT + 'availability_by_horizon_mimic.csv')
dca = pd.read_csv(OUT + 'dca_lm24_common.csv')

D = []
D.append("""# CS-MORT-6: Supplementary Material (revision draft)

Supplement to the International Journal of Cardiology Short Communication,
revision of IJCJOURNAL-D-26-03573. Draft for author review; Word formatting
(Times New Roman, three-rule tables, 10 pt italic legends) applied at build.
Every value derives from the archived analysis pipeline; source files are
named per table for the number-by-number audit.
""")

D.append("""## Table S1. TRIPOD+AI reporting checklist
Updated for the landmark-primary revision (full checklist reproduced at Word
build from the submitted version, with locations revised; items 10 and 12
now reference the landmark eligibility rule and the influence-function
confidence interval).""")

D.append("""## Table S2. Definitions, landmark eligibility, and missing-component rule

(A) Variable definitions and measurement windows: lactate, blood urea
nitrogen, and red cell distribution width as the most recent value up to 24
hours; urine output as cumulative first-24-hour volume divided by weight and
observed hours (fixed 24-hour denominator in eICU); age and out-of-hospital
cardiac arrest (cardiac-arrest diagnosis with emergency admission in eICU)
as admission characteristics; harmonized anion gap as most recent sodium
minus chloride minus bicarbonate. MIMIC-IV phenotype: diagnostic code or
affirmed discharge-summary documentation plus at least one objective
hypoperfusion criterion within 24 hours (systolic blood pressure < 90 mmHg,
mean arterial pressure < 65 mmHg, lactate >= 2 mmol/L, or vasoactive,
inotropic, or mechanical circulatory support). eICU cohort: APACHE
cardiogenic shock diagnosis string.

(B) Landmark eligibility: alive and in the ICU at 24 hours from ICU
admission, defined as ICU discharge at or after, and no recorded death at or
before, 24 hours. Of 3,103 development patients, 2,694 met the landmark; 251
had death timestamps at or before the landmark (two anomalously preceding
ICU admission, disclosed in Table S7), 156 were discharged alive before 24
hours, and 2 had indeterminate ICU discharge times and were excluded. No
death or discharge is timestamped at exactly 24 hours, so boundary
convention does not affect any count. The landmark cohort's 892 deaths for
six predictors exceed recommended minimum sample size.

(C) Missing-component rule (deployment): a missing component scores the
category of the development-cohort median value: lactate and anion gap the
lowest band (medians 1.9 and 13.0), urine output the middle band (0.73),
age and blood urea nitrogen the middle bands (71.0; 33.0), red cell
distribution width the middle band (15.2).""")

D.append("## Table S3. Full model specification (landmark estimation)\n\n(A) Continuous models, exact values (source: v2_spec_continuous.csv)\n\n"
         + md(spec.fillna('')) +
"""

Predicted probability = 1 / (1 + exp(-(intercept + sum of beta x z))), with
z = (winsorized, median-imputed value - mean) / SD; the raw-scale column
allows direct computation from raw values. Worked example (Word build): a
72-year-old with lactate 3.1 mmol/L, urine output 0.4 mL/kg/h, no OHCA, BUN
41 mg/dL, RDW 15.9%.

(B) Integer card (points per category; range 0-15)

""" + md(card) + """

Anion-gap substitution when lactate is unavailable: < 12 / 12-18 / >= 18
scored 0 / 2 / 4. Thresholds are left-inclusive.

(C) Score-to-risk mapping at the landmark (source: v2_score_risk_mapping.csv)

""" + md(mapping))

D.append("""## Table S4. Model development and card-stability sensitivity

(A) Model-class comparison. Conducted during development on the wider
candidate pool of the development cohort (provenance: this comparison
predates the final six-variable model, which is why its values differ from
the final model's): penalized logistic regression 0.792 (calibration slope
0.93), LASSO 0.792 (0.95), random forest 0.790 (1.61), gradient boosting
0.796 (0.75). Penalized logistic regression was selected for calibration
stability and the transparent integer card it supports.

(B) Landmark re-derivation sensitivity for the point schedule. Re-deriving
points at the landmark was unstable across 500 bootstrap re-derivations
(lactate 1 point in 64% versus 2 points in 36%; OHCA 3 points in 61% versus
2 in 39%) and did not improve validated discrimination (transported card
minus re-derived card +0.0055, 95% CI -0.000 to +0.011). The transported
point schedule was therefore retained.""")

D.append("""## Table S5. Baseline characteristics

Reproduced from the submitted supplement (full documented-cardiogenic-shock
cohorts; the severity frame), with landmark counts referenced in Table S2.
Regenerated at Word build from the archived aggregate tables.""")

D.append("""## Table S6. Day-1 severity-frame performance (all admissions)

Regenerated by the canonical pipeline under corrected thresholds; these
estimates correspond to the submitted design and are retained for
comparability with existing scores.

| Metric | MIMIC-IV (n=3,103) | eICU (n=1,866; 132 hospitals) |
|---|---|---|
| Continuous, lactate | 0.778 (0.760-0.794) | 0.757 (0.733-0.780) |
| Continuous, anion gap | 0.762 (0.744-0.779) | 0.749 (0.725-0.772) |
| Integer card | 0.758 (0.740-0.774) | 0.732 (0.709-0.755) |
| Calibration, anion gap | slope 0.98 (internal) | slope 0.96, CITL +0.04 |
| BOS,MA2 head-to-head (n=1,127) | - | 0.749 vs 0.743; diff +0.006 (-0.026 to +0.038); P = .69 |

Exploratory sensitivity: scored on all landmark patients after
chained-equations imputation of missing checklist components (analogous to,
not a replication of, the predictive-mean-matching imputation of its
development study), BOS,MA2 reached 0.684 versus 0.715 for CS-MORT-6 anion
gap (difference +0.032, 95% CI +0.001 to +0.062). eICU served as BOS,MA2's
development data.""")

D.append("## Table S7. Death-timing distribution, exact timestamps (source: event_time_exact.csv)\n\n" + md(evt) +
"""

Two records carry death timestamps preceding ICU admission and one death has
no timestamp; all three are retained in mortality counts and disclosed here.
65.6% of deaths occur after 48 hours.""")

D.append("## Table S8. Landmark risk bands and threshold operating characteristics\n\n(A) Risk bands, out-of-fold (source: v2_risk_bands_oof.csv); eICU external bands in the locked-run results\n\n"
         + md(bands) + """

eICU landmark (frozen card): Low 12.7% (9.9-16.1, n=450), Moderate 24.0%
(20.4-28.0, n=488), High 42.6% (37.7-47.6, n=376), Very high 52.9%
(47.0-58.8, n=272).

(B) Diagnostic accuracy at integer thresholds, landmark population (source:
landmark_thresholds.csv)

""" + md(thr_tab))

D.append("## Table S9. Within-stage resolution and incremental value\n\n(A) Within-stage tertile mortality, exact landmark (sources: figure1_mimic_lm24.csv, figure1_eicu_lm24.csv)\n\n"
         + md(pd.concat([f1m, f1e])) + """

(B) Incremental value (MIMIC-IV, landmark): EHR-derived stage alone AUROC
0.589; score alone 0.727; stage plus score 0.728; adding score to stage
+0.139 (95% CI +0.116 to +0.163; likelihood-ratio chi-square 348.2,
P < .001); adding stage to score +0.001. Within-stage AUROC: B 0.636
(0.579-0.692), C 0.689 (0.651-0.724), D 0.756 (0.717-0.793), E 0.728
(0.689-0.765).

(C) Robustness of the gradient: tertile mortality by stage using the
OHCA-free card (MIMIC B 16/30/37, C 16/35/46, D 13/27/58, E 30/49/73) and a
four-variable sub-score of variables taking no part in staging (B 16/32/36,
C 15/32/46, D 12/34/53, E 35/51/68).""")

D.append("## Table S10. 48-hour reassessment and score trajectory\n\n" + """
(A) Reapplication of the frozen landmark model at 48 hours. MIMIC (n=2,259,
703 deaths): updated 48-hour values 0.739 (0.717-0.760; slope 1.10, CITL
+0.03) versus stale 24-hour prediction 0.714; paired difference +0.024 (95%
CI +0.012 to +0.036). eICU (n=1,316, 368 deaths): anion gap updated 0.696
(0.664-0.726; slope 0.87, CITL 0.00) versus stale 0.680; paired difference
+0.015 (95% CI -0.003 to +0.034). This is a reassessment of the 24-hour
model, not a separately fitted 48-hour landmark model.

(B) Symmetric trajectory (source: trajectory_symmetric.csv)

""" + md(traj) + """

Adjusted odds ratio per one-point 24-to-48-hour increase, adjusted for the
24-hour score: 1.37 (95% CI 1.27-1.47), P < .001; generator archived in the
pipeline.""")

D.append("## Table S11. Observed-data availability and scorability\n\n" + """
(A) Exact 24-hour landmark. MIMIC-IV: lactate 80.8%, anion gap 99.6%, urine
output 94.2%, BUN 99.7%, RDW 99.1%; all anion-gap-model inputs 93.2%; all
lactate-model inputs 75.6%. eICU: lactate 48.7%, anion gap 96.5%, urine
output 58.7%, BUN 97.4%, RDW 89.3%; all anion-gap-model inputs 52.0%; all
lactate-model inputs 26.0%.

(B) eICU 48-hour landmark (cumulative): anion gap 98.9%, BUN 99.5%, RDW
93.0%, urine output 62.3%, lactate 53.6%; all anion-gap-model inputs 58.2%.

(C) Availability by horizon, MIMIC in-ICU populations (temporal trend;
source: availability_by_horizon_mimic.csv)

""" + md(avail))

D.append("## Table S12. Sensitivity analyses, imputation, and collinearity\n\n" + """
(A) Sensitivity cohorts (landmark, frozen model out-of-fold): ICD-confirmed
only 0.734 (n=2,452), Sepsis-3 excluded 0.747 (n=1,321), non-OHCA subgroup
0.724 (n=2,438), OHCA-free integer card 0.711.

(B) Imputation: median 0.734 (slope 0.99) versus multiple imputation by
chained equations 0.724 (slope 1.01).

(C) Variance inflation factors (landmark): lactate model, all at or below
1.16; anion-gap model, all at or below 1.31 (largest: BUN). Pearson
correlations (source: correlation_matrix_lm24.csv):

""" + md(corr.reset_index()))

D.append("## Table S13. Subgroup discrimination and calibration (landmark; source: fairness_subgroups_lm24.csv)\n\n" + md(fair) + """

Recorded race is a social classification; differences may reflect
measurement frequency, case mix, admission pathways, and site. The
Other/Unknown category is heterogeneous. Site-level recalibration and
equity monitoring are recommended before deployment; race-specific
correction and fairness-weighted training were deliberately not applied.""")

D.append("## Table S14. Redevelopment sensitivity analyses\n\n" + """
Fully nested redevelopment (selection inside 10-times-repeated 5-fold outer
cross-validation; decision rule specified and archived before execution).
Deployable pool (13 candidates with harmonized definitions and >= 80%
availability in both databases): 0.718 versus 0.733 for the six-variable
model; paired difference -0.014 (95% CI -0.029 to +0.001). Symmetric pool
(lactate and urine output restored): 0.725; paired difference -0.007 (95%
CI -0.020 to +0.005). Neither met the pre-stated replacement criteria.

Outer-fold selection frequencies (source: challenger_selection.csv,
challenger_symmetric_selection.csv):

""" + md(selS) + """

The low landmark reselection of lactate (38%) and urine output (6%) is a
limitation; their retention rests on their prior selection and inclusion in
the developed model and on neither redevelopment analysis demonstrating
improved validated performance.""")

nb20 = dca.iloc[(dca['threshold'] - 0.20).abs().argmin()]
nb40 = dca.iloc[(dca['threshold'] - 0.40).abs().argmin()]
D.append(f"""## Table S15. Decision-curve analysis (landmark, common-scorable; exploratory)

Primary comparison with frozen published probabilities for both models: at
the 20% threshold, net benefit {nb20['cs_mort6_ag']:.3f} (CS-MORT-6 anion gap) versus
{nb20['bosma2_published']:.3f} (BOS,MA2 published mapping); at 40%, {nb40['cs_mort6_ag']:.3f} versus
{nb40['bosma2_published']:.3f}. A BOS,MA2 curve recalibrated within the evaluation sample
({nb20['bosma2_recal']:.3f} and {nb40['bosma2_recal']:.3f}) is shown as a labeled in-sample sensitivity that
favors the comparator. Curve data: dca_lm24_common.csv.""")

D.append("""## Supplementary figure legends

Figure S1. Cohort derivation flow, including the 24-hour landmark and its
exclusion decomposition, both cohorts.
Figure S2. Calibration of CS-MORT-6 at the landmark: internal out-of-fold
deciles (both formulations) and eICU external anion gap. Sources:
v2_calibration_curve_oof_lac.csv, v2_calibration_curve_oof_ag.csv.
Figure S3. Decision curves, landmark common-scorable set: frozen-vs-frozen
primary with the in-sample recalibrated comparator as sensitivity. Source:
dca_lm24_common.csv.
Figure S4. Within-stage tertile mortality using the OHCA-free card and the
four-variable non-staging sub-score.
Figure S5. Score trajectory at the 48-hour landmark, symmetric definition,
with the intermediate-score subgroup shown separately.
Figure S6. Subgroup discrimination and calibration at the landmark.
Figure S7. Nomogram of the continuous anion-gap landmark model.""")

open(DOC, 'w').write('\n\n'.join(D) + '\n')
print(f"supplement draft written: {len(D)} sections")
print("landmark threshold table:")
print(thr_tab.to_string(index=False))
