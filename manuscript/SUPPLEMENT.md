# CS-MORT-6: Supplementary Material (revision draft)

Supplement to the International Journal of Cardiology Short Communication,
revision of IJCJOURNAL-D-26-03573. Draft for author review; Word formatting
(Times New Roman, three-rule tables, 10 pt italic legends) applied at build.
Numerical results derive from the analyses described in the Methods unless the
table states otherwise.

Abbreviations used throughout: AUROC, area under the receiver operating
characteristic curve; CI, confidence interval; CITL, calibration-in-the-large;
SD, standard deviation; BUN, blood urea nitrogen; RDW, red cell distribution
width; UO, urine output; MCS, mechanical circulatory support; SCAI, Society
for Cardiovascular Angiography and Interventions.

## Supplementary Methods

### Cohort definition and landmark eligibility

The MIMIC-IV phenotype's physiological and support criteria are systolic
blood pressure < 90 mmHg, mean arterial pressure < 65 mmHg, lactate ≥2
mmol/L, or vasoactive, inotropic, or mechanical circulatory support, within
24 hours. Landmark eligibility is ICU discharge at or after, and no recorded
death at or before, 24 hours; no record falls at exactly 24 hours.

### Predictor measurement

The harmonized anion gap is sodium minus chloride minus bicarbonate, each
component its own most recent value rather than a single draw. Urine output
is cumulative volume divided by weight and observed hours, with a fixed
denominator in eICU. Cardiac arrest is a diagnosis-record indicator without
an event timestamp: in MIMIC-IV a hospital-admission discharge diagnosis
(ICD-10 I46.x or ICD-9 427.5) with emergency or urgent admission, which
cannot establish that the arrest preceded ICU admission or the landmark; in
eICU a structured cardiac-arrest diagnosis documented by the landmark, whose
offset records documentation rather than onset.

### Sample size and predictor screen

Minimum sample size follows Riley et al (pmsampsize: binary outcome,
anticipated C-statistic 0.70, observed outcome proportion, stated parameter
count, target shrinkage 0.9, margin of error 0.05). Re-estimating the six
fixed predictors at the landmark (outcome proportion 0.331) requires 469
patients with 156 events. The development-time predictor screen evaluated 58
candidate
parameters in 4,315 ICU stays from 3,192 patients (1,537 deaths), using 400
bootstrap resamples of L1-penalized logistic regression; 38 parameters were
selected (absolute coefficient above 1e-6) in at least 80% of resamples, five
of the six retained predictors in 400 of 400, and blood urea nitrogen in 399
of 400. Parameters requiring imaging, neurological assessment,
treatment-dependent measurement, or additional hemodynamic information were
not carried into a bedside score. The screen treated repeated stays as
independent and did not meet its own requirement of 4,386 observations with
1,563 events; nested redevelopment placing selection inside 10-times-repeated
5-fold cross-validation (Table S9) assesses robustness to the selection step.

### Integer scoring and missing data

When neither lactate nor anion gap is observed, the component scores the
anion-gap development-median category (2 points); an absent arrest record
scores as no arrest. Availability in Table S5 is observed data; after these
rules every patient is evaluable.

### Sensitivity and 48-hour analyses

The imputation sensitivity replaced the median rule with a single stochastic
chained-equations imputation, fitted within each training fold and applied to
its test fold, as were the winsorization limits, without multiple-imputation
pooling; this gave AUROC 0.725 and calibration slope 1.01, versus 0.734 and
0.99 under the median rule. In the 48-hour analyses, laboratory predictors
take the most recent
value up to 48 hours and urine output is cumulative over the horizon. The 5
arrest flags first entered after 24 hours are zeroed in the primary external
analyses; the 48-hour analyses apply the same rule at 2,880 minutes.

## Table S1. TRIPOD+AI reporting checklist

Items 10 and 12 reference the landmark eligibility rule and the
influence-function confidence interval.

## Table S2. EHR-derived SCAI stage rules

| Stage | MIMIC-IV, first 24 hours | eICU |
|---|---|---|
| E | Cardiac arrest, ≥3 vasoactive agents (vasopressor count plus inotrope use), or ≥2 MCS devices | Any recorded cardiac-arrest diagnosis |
| D | 2 vasoactive agents, any device, or maximum lactate > 4 mmol/L on ≥1 vasoactive agent | Any recorded mechanical support interface |
| C | ≥1 vasoactive agent, or maximum lactate ≥2 mmol/L with hypotension (minimum systolic < 90 or minimum mean < 65 mmHg) | Any vasopressor or inotrope |
| B | Hypotension or maximum lactate ≥2 mmol/L | Otherwise |
| A | Otherwise | Not assignable |

Rules apply in the order E, D, C, B; the first matching rule assigns the
stage. MIMIC-IV stage A is assigned when no rule matches; eICU stage A is not
assignable because all cohort members meet the shock definition. The eICU
stage-E rule accepts any recorded cardiac-arrest diagnosis without the
emergency-admission restriction of the score's arrest predictor, so 238 of
1,047 primary-landmark patients are staged E while 147 carry the arrest
point. These pragmatic rules follow the 2022 update's therapy-intensity
guidance for stages C through E and are not the operationalization of
Jentzer et al.

## Table S3. Full model specification (landmark estimation)

(A) Continuous models, exact values

| Model | Variable | Winsor low | Winsor high | Impute median | Mean | SD | z-scale beta | Raw-scale beta |
|---|---|---|---|---|---|---|---|---|
| Lactate | Lactate | 0.7 | 12.723 | 1.9 | 2.418 | 1.8608 | 0.496888 | 0.267033 |
| Lactate | Urine output | 0.0013 | 3.8352 | 0.728 | 0.9197 | 0.7526 | -0.427892 | -0.568569 |
| Lactate | Cardiac arrest | 0.0 | 1.0 | 0.0 | 0.095 | 0.2933 | 0.325232 | 1.109057 |
| Lactate | Age | 27.93 | 93.0 | 71.0 | 69.6641 | 14.0336 | 0.263458 | 0.018773 |
| Lactate | Blood urea nitrogen | 8.0 | 122.16 | 33.0 | 39.2072 | 24.9254 | 0.254663 | 0.010217 |
| Lactate | Red cell distribution width | 12.2 | 24.496 | 15.2 | 15.7704 | 2.4865 | 0.198363 | 0.079777 |
| Lactate | (intercept) | | | | | | -0.806673 | -4.001369 |
| Anion gap | Anion gap | 5.0 | 29.0 | 13.0 | 13.3935 | 4.5533 | 0.427884 | 0.093973 |
| Anion gap | Urine output | 0.0013 | 3.8352 | 0.728 | 0.9197 | 0.7526 | -0.463905 | -0.616421 |
| Anion gap | Cardiac arrest | 0.0 | 1.0 | 0.0 | 0.095 | 0.2933 | 0.361791 | 1.233727 |
| Anion gap | Age | 27.93 | 93.0 | 71.0 | 69.6641 | 14.0336 | 0.271008 | 0.019311 |
| Anion gap | Blood urea nitrogen | 8.0 | 122.16 | 33.0 | 39.2072 | 24.9254 | 0.082329 | 0.003303 |
| Anion gap | Red cell distribution width | 12.2 | 24.496 | 15.2 | 15.7704 | 2.4865 | 0.186597 | 0.075044 |
| Anion gap | (intercept) | | | | | | -0.82333 | -4.290575 |

Predicted probability = 1 / (1 + exp(-(intercept + sum of beta x z))), with z
= (winsorized, median-imputed value - mean) / SD; the raw-scale column allows
direct computation from winsorized, median-imputed values without
standardization. The arrest indicator is not restricted to out-of-hospital
arrest. Worked example (lactate formulation): a 72-year-old with lactate 3.1
mmol/L, urine output 0.4 mL/kg/h, no arrest, BUN 41 mg/dL, RDW 15.9%: linear
predictor -0.362, predicted probability 0.41; the integer card gives 2 + 2 +
0 + 1 + 1 + 1 = 7 points, mapped predicted risk 44.9%, against observed
landmark mortality at score 7 of 42.5% (panel C).

(B) Integer card (points per category; total range 0 to 15)

| Variable | Categories (points) | Development median (points if missing, internal) |
|---|---|---|
| Lactate, mmol/L | < 2 (0); 2 to < 4 (2); ≥4 (4) | 1.9 (0) |
| Anion gap, mmol/L, when lactate unavailable | < 12 (0); 12 to < 18 (2); ≥18 (4) | 13.0 (2) |
| Urine output, mL/kg/h | ≥1 (0); 0.5 to < 1 (1); < 0.5 (2) | 0.73 (1) |
| Cardiac arrest | no (0); yes (3) | no (0) |
| Age, years | < 65 (0); 65 to < 80 (1); ≥80 (2) | 71.0 (1) |
| Blood urea nitrogen, mg/dL | < 25 (0); 25 to < 45 (1); ≥45 (2) | 33.0 (1) |
| Red cell distribution width, % | < 14.5 (0); 14.5 to < 16 (1); ≥16 (2) | 15.2 (1) |

Apply the intervals exactly as printed: a urine output of 0.5 mL/kg/h scores
1 point and 1.0 mL/kg/h scores 0 points, because higher output is protective.
The final column is the internal missing-component default (edge cases in
the Supplementary Methods). The continuous anion-gap model (panel A) is a
separately fitted model, not a substitution into the lactate equation.

(C) Score-to-risk mapping at the landmark (observed mortality drawn in Figure
S4)

| Score | Predicted risk, % | Observed mortality at the landmark |
|---|---|---|
| 0 | 7.2 | 5.6% (n=71) |
| 1 | 9.8 | 6.9% (n=130) |
| 2 | 13.2 | 11.2% (n=240) |
| 3 | 17.5 | 17.8% (n=314) |
| 4 | 22.9 | 24.2% (n=384) |
| 5 | 29.4 | 31.5% (n=387) |
| 6 | 36.8 | 38.2% (n=364) |
| 7 | 44.9 | 42.5% (n=294) |
| 8 | 53.3 | 54.1% (n=196) |
| 9 | 61.5 | 58.2% (n=141) |
| 10 | 69.1 | 69.2% (n=78) |
| 11 | 75.8 | 75.5% (n=53) |
| 12 | 81.4 | 81.5% (n=27) |
| 13 | 86.0 | n<10 |
| 14 | 89.6 | n<10 |
| 15 | 92.3 | n<10 |

(D) Point-schedule sensitivity. Using the existing cross-validation folds, the
original point schedule had an out-of-fold AUROC of 0.7267, compared with
0.7190 when point weights were re-derived within each training fold
(difference 0.0076, 95% CI 0.0034-0.0121). The original point schedule
remained the primary specification.

## Table S4. Baseline characteristics of the landmark analysis populations

Continuous variables are median (interquartile range) and categorical
variables n (%).

## Table S5. Observed-data availability and scorability

Component availability, % of patients:

| Input | MIMIC-IV 24 h (n=2,694) | eICU primary 24 h (n=1,047) | eICU primary 48 h |
|---|---|---|---|
| Lactate | 80.8 | 52.5 | 56.9 |
| Anion gap | 99.6 | 96.4 | 98.6 |
| Urine output | 94.2 | 60.6 | 64.8 |
| Blood urea nitrogen | 99.7 | 97.4 | 99.4 |
| Red cell distribution width | 99.1 | 89.5 | 93.8 |
| All anion-gap-model inputs | 93.2 | 53.3 | 60.7 |
| All lactate-model inputs | 75.6 | 29.5 | - |

The 24-hour columns are the exact landmark; 48-hour values are cumulative; a
dash marks a quantity not evaluated. Availability rose with horizon: lactate
was observed in 69.2% of patients in the ICU at 6 hours, 80.8% at 24 hours,
and 85.9% at 48 hours, with blood urea nitrogen, red cell distribution
width, and urine output at or above 94.2% by 24 hours (denominators count
patients in the ICU at each whole-hour boundary, n=2,731 at 24 hours, a
coarser flag than the exact-timestamp landmark).

## Table S6. Sensitivity analyses and collinearity

(A) Sensitivity cohorts (landmark, frozen model out-of-fold)

| Analysis | n | AUROC |
|---|---|---|
| ICD-confirmed only | 2,452 | 0.734 |
| Sepsis-3 excluded | 1,321 | 0.747 |
| No-arrest subgroup | 2,438 | 0.724 |
| Arrest-free integer card | - | 0.711 |

(B) Variance inflation factors, every predictor, both formulations (landmark,
on the winsorized, imputed, standardized design)

| Predictor | Lactate model | Anion-gap model |
|---|---|---|
| Lactate / anion gap | 1.05 | 1.22 |
| Urine output | 1.08 | 1.06 |
| Cardiac arrest | 1.02 | 1.01 |
| Age | 1.08 | 1.08 |
| Blood urea nitrogen | 1.16 | 1.31 |
| Red cell distribution width | 1.10 | 1.11 |

Correlations were 0.00 for lactate and blood urea nitrogen, 0.06 for lactate
and red cell distribution width, and 0.28 for blood urea nitrogen and red
cell distribution width; the largest in either formulation is anion gap with
blood urea nitrogen at 0.37. The full correlation matrix is in the repository
outputs (correlation_matrix_lm24.csv).

## Table S7. Landmark risk bands and threshold operating characteristics

(A) Risk bands. MIMIC-IV landmark, out-of-fold:

| Band | n | Deaths | Mortality, % | CI |
|---|---|---|---|---|
| Low 0-3 | 755 | 96 | 12.7 | 10.5-15.3 |
| Moderate 4-5 | 771 | 215 | 27.9 | 24.8-31.2 |
| High 6-7 | 658 | 264 | 40.1 | 36.4-43.9 |
| Very high 8-15 | 510 | 317 | 62.2 | 57.9-66.3 |

eICU primary landmark (deployment-rule card, locked external run):

| Band | n | Mortality, % | CI |
|---|---|---|---|
| Low 0-3 | 296 | 8.8 | 6.1-12.6 |
| Moderate 4-5 | 292 | 18.8 | 14.8-23.7 |
| High 6-7 | 245 | 39.6 | 33.7-45.8 |
| Very high 8-15 | 214 | 59.3 | 52.7-65.7 |

External mapped-risk calibration slope 1.15, CITL -0.22; decile calibration
curves are Figure S2. Rescoring the internal cohort under the external
deployment rule (anion-gap bands for the 19.2% of patients without an
observed lactate) gives AUROC 0.720, versus 0.727 under the
missing-component rule.

(B) Diagnostic accuracy at integer thresholds, landmark population (internal
missing-component rule, Table S3 panel B)

| Threshold | Sensitivity | Specificity | PPV | NPV | LR+ | LR- |
|---|---|---|---|---|---|---|
| ≥4 | 0.89 | 0.37 | 0.41 | 0.87 | 1.41 | 0.29 |
| ≥6 | 0.65 | 0.67 | 0.50 | 0.80 | 2.00 | 0.52 |
| ≥8 | 0.36 | 0.89 | 0.62 | 0.74 | 3.32 | 0.72 |
| ≥9 | 0.24 | 0.94 | 0.67 | 0.71 | 4.14 | 0.81 |

PPV, positive predictive value; NPV, negative predictive value; LR+ and LR-,
positive and negative likelihood ratios.

## Table S8. External populations and day-1 performance

(A) External landmark populations (frozen model unchanged)

| Population | n | Deaths | Anion-gap AUROC | Deployment-rule card | AG-bands card |
|---|---|---|---|---|---|
| Primary: one stay/patient, shock documented by 24 h | 1,047 | 305 | 0.748 (0.715-0.780) | 0.759 (0.729-0.790) | 0.738 (0.707-0.770) |
| One stay/patient, any-time documentation | 1,439 | 453 | 0.716 (0.688-0.745) | - | 0.702 (0.674-0.731) |
| All landmark stays | 1,586 | 478 | 0.713 (0.685-0.739) | - | 0.697 (0.669-0.724) |

The 1,586 landmark stays comprise 1,439 unique patients (147 repeat stays);
late-documented eligibility and repeat stays each attenuated discrimination.
Retaining the five arrest flags first documented after 24 hours gives anion
gap 0.747 and deployment-rule card 0.758.

(B) Day-1 performance among all admissions (retained for comparability with
existing scores; repeat stays included)

| Metric | MIMIC-IV (n=3,103) | eICU (1,866 stays; 132 hospitals) |
|---|---|---|
| Continuous, lactate | 0.778 (0.760-0.794) | 0.757 (0.735-0.780) |
| Continuous, anion gap | 0.762 (0.744-0.779) | 0.749 (0.726-0.772) |
| Integer card | 0.758 (0.740-0.774) | 0.732 (0.709-0.755) |
| Calibration | out-of-fold slope 0.98 (lactate formulation) | anion gap slope 0.96, CITL +0.04 |
| BOS,MA2 head-to-head, day 1 (n=1,127) | - | 0.749 vs 0.743; diff +0.006 (-0.026 to +0.037) |
| BOS,MA2 imputed-all sensitivity (landmark, n=1,047) | - | 0.748 vs 0.735; diff +0.014 (-0.024 to +0.050) |
| BOS,MA2 common-scorable landmark (n=654) | - | 0.755 vs 0.751; diff +0.004 (-0.039 to +0.046) |

The integer card is scored under each cohort's missing-component rule; the
AG-bands column scores every patient on anion-gap bands (harmonized
sensitivity). BOS,MA2 rows give CS-MORT-6 anion gap first; the
imputed-all row fills missing components by chained equations, not a
replication of the development study's predictive-mean-matching. Of the eICU
database's 208 hospitals, 132 contributed the 1,866-stay cohort and 117 the
primary landmark population.

## Table S9. Model-class comparison and redevelopment sensitivity analyses

(A) Model-class comparison (development, day-1 cohort)

| Model | AUROC | Calibration slope |
|---|---|---|
| Ridge-penalized logistic regression (selected) | 0.792 | 0.93 |
| LASSO | 0.792 | 0.95 |
| Random forest | 0.790 | 1.61 |
| Gradient boosting | 0.796 | 0.75 |

This historical comparison used a wider candidate pool than the final
six-variable model, so its values differ from the final model's and from the
nested landmark redevelopment below.

(B) Nested redevelopment against the six-variable model's 0.733 on the same
folds:

| Pool | Candidates | Redeveloped AUROC | Paired difference (95% CI) |
|---|---|---|---|
| Deployable: harmonized definitions, ≥80% availability in both databases | 13 | 0.718 | -0.014 (-0.029 to +0.001) |
| Symmetric: lactate and urine output restored | 15 | 0.725 | -0.007 (-0.020 to +0.005) |

Neither pool met the replacement criteria, which are stated in full in the
frozen challenger-analysis section of the archived analysis protocol. Across
outer folds, age, cardiac arrest, and red cell distribution width were
selected in 100% of resamples in both pools, the harmonized anion gap in 88%
and 50%, blood urea nitrogen in 76% and 98%, and minimum systolic blood
pressure in 70% and 78%; every other candidate was selected in 26% or fewer
of resamples. The low landmark reselection of lactate (38%) and urine output
(6%), evaluable only in the symmetric pool, is a limitation; their retention
rests on their prior selection and inclusion in the developed model and on
neither redevelopment analysis demonstrating improved validated performance.

## Table S10. Within-stage resolution and incremental value

(A) Within-stage tertile mortality, exact landmark

| Cohort | Stage | Tertile | n | Mortality, % | 95% CI |
|---|---|---|---|---|---|
| MIMIC | B | Low | 168 | 16.1 | 11.3-22.4 |
| MIMIC | B | Mid | 135 | 29.6 | 22.6-37.8 |
| MIMIC | B | High | 104 | 36.5 | 27.9-46.1 |
| MIMIC | C | Low | 419 | 16.0 | 12.8-19.8 |
| MIMIC | C | Mid | 257 | 35.4 | 29.8-41.4 |
| MIMIC | C | High | 233 | 45.9 | 39.6-52.3 |
| MIMIC | D | Low | 310 | 13.2 | 9.9-17.5 |
| MIMIC | D | Mid | 202 | 26.7 | 21.1-33.2 |
| MIMIC | D | High | 187 | 57.8 | 50.6-64.6 |
| MIMIC | E | Low | 236 | 26.7 | 21.5-32.7 |
| MIMIC | E | Mid | 262 | 49.2 | 43.2-55.3 |
| MIMIC | E | High | 173 | 73.4 | 66.4-79.4 |
| eICU | B | Low | 129 | 7.0 | 3.7-12.7 |
| eICU | B | Mid | 69 | 27.5 | 18.4-39.0 |
| eICU | B | High | 66 | 36.4 | 25.8-48.4 |
| eICU | C | Low | 173 | 11.6 | 7.6-17.2 |
| eICU | C | Mid | 108 | 28.7 | 21.0-37.9 |
| eICU | C | High | 99 | 53.5 | 43.8-63.0 |
| eICU | D | Low | 73 | 8.2 | 3.8-16.8 |
| eICU | D | Mid | 44 | 15.9 | 7.9-29.4 |
| eICU | D | High | 48 | 45.8 | 32.6-59.7 |
| eICU | E | Low | 106 | 33.0 | 24.8-42.4 |
| eICU | E | Mid | 59 | 54.2 | 41.7-66.3 |
| eICU | E | High | 73 | 64.4 | 52.9-74.4 |

Tied integer values make tertile sizes unequal. Stage A (n=8, no deaths) is
not tabulated; these eight patients met the cohort hypoperfusion criterion
through measurements outside the staging component set (seven had no lactate
in the staging window), so absent components under-stage them.

(B) Incremental value

| Cohort | Formulation | Stage only | Score only | Stage + score | Difference (95% CI) |
|---|---|---|---|---|---|
| MIMIC-IV | Integer card | 0.589 | 0.727 | 0.728 | +0.139 (+0.116 to +0.163) |
| MIMIC-IV | Continuous anion gap | 0.589 | 0.726 | 0.728 | +0.139 (+0.116 to +0.162) |
| eICU | Continuous anion gap | 0.613 | 0.748 | 0.754 | +0.141 (+0.101 to +0.178) |
| eICU | Integer card | 0.613 | 0.759 | 0.767 | +0.154 (+0.116 to +0.191) |

Within-stage AUROC: B 0.636 (0.579-0.692), C 0.689 (0.651-0.724), D 0.756
(0.717-0.793), E 0.728 (0.689-0.765); likelihood-ratio chi-square for the
score over the stage 348.2 in MIMIC-IV, P < .001 throughout. With the arrest
rule removed from staging the increments are +0.165 (continuous) and +0.164
(integer) over stage 0.564 in MIMIC-IV, and +0.226 and +0.237 over 0.524 in
eICU. Treating the stage as unordered categories (examined because eICU
stage-specific mortality is not monotone; stage-only AUROC 0.630 versus
0.613 for the ordinal term in eICU, and 0.589 in MIMIC-IV) left the
increments essentially unchanged: +0.140 (95% CI +0.115 to +0.161) for the
continuous anion-gap model and +0.142 (+0.117 to +0.162) for the integer
card in MIMIC-IV, and +0.125 (+0.090 to +0.160) and +0.135 (+0.102 to
+0.174) in eICU; refitting the stage-only and stage-plus-score models within
each resample left that interval at +0.104 to +0.178 versus the reported
+0.101 to +0.178 for the eICU continuous anion-gap model.

(C) Transportability of within-stage thresholds: MIMIC-frozen per-stage
tertile cutpoints applied unchanged to the eICU primary landmark

| Stage | Score ranges (low/mid/high) | n (low/mid/high) | Mortality low/mid/high, % |
|---|---|---|---|
| B | 0-3 / 4-5 / 6-15 | 82/89/93 | 2.4 / 20.2 / 34.4 |
| C | 0-4 / 5-6 / 7-15 | 173/108/99 | 11.6 / 28.7 / 53.5 |
| D | 0-4 / 5-6 / 7-15 | 97/35/33 | 12.4 / 14.3 / 54.5 |
| E | 0-5 / 6-8 / 9-15 | 78/87/73 | 23.1 / 56.3 / 64.4 |

Mortality is monotonic in every stage. The sample-tertile cells in panel A
are descriptive; panel C evaluates fixed, transported thresholds.

## Table S11. Subgroup discrimination and calibration

Landmark population; predictions are the lactate-formulation out-of-fold
estimates. Source race strings are grouped as White, Black, Hispanic, Asian,
and Other/Unknown (the last combines 119 Other and 574 Unknown or declined in
the full cohort); the sex rows and the race rows each total the 2,694 landmark
patients. Figure S7 plots discrimination and calibration-in-the-large by
subgroup.

| Subgroup | n | Deaths | AUROC | CI | Slope | CITL |
|---|---|---|---|---|---|---|
| Male | 1,629 | 519 | 0.748 | 0.724-0.774 | 1.07 | -0.062 |
| Female | 1,065 | 373 | 0.713 | 0.682-0.746 | 0.89 | 0.092 |
| White | 1,687 | 537 | 0.732 | 0.706-0.757 | 1.03 | -0.067 |
| Black | 267 | 80 | 0.704 | 0.631-0.771 | 0.81 | -0.298 |
| Hispanic | 80 | 24 | 0.805 | 0.692-0.903 | 1.21 | -0.107 |
| Asian | 67 | 17 | 0.708 | 0.548-0.851 | 0.68 | -0.374 |
| Other/Unknown | 593 | 234 | 0.754 | 0.715-0.792 | 1.07 | 0.362 |

Recorded race is a social classification, and the Other/Unknown category is
heterogeneous. Estimates for the Hispanic and Asian groups were imprecise
because of small sample sizes.

## Table S12. 48-hour reassessment and score trajectory

(A) Reapplication of the frozen landmark model at 48 hours

| Cohort (formulation) | n | Deaths | Updated 48-h AUROC (95% CI) | Slope | CITL | Carried-forward 24-h AUROC | Paired difference (95% CI) |
|---|---|---|---|---|---|---|---|
| MIMIC-IV (continuous lactate) | 2,259 | 703 | 0.739 (0.717-0.760) | 1.10 | +0.03 | 0.714 | +0.024 (+0.012 to +0.036) |
| eICU primary (anion gap) | 806 | 202 | 0.725 (0.685-0.765) | 1.07 | -0.14 | 0.716 | +0.009 (-0.012 to +0.030) |

The carried-forward eICU prediction has slope 0.99, CITL -0.20.

(B) Symmetric trajectory (plotted in Figure S6)

| Scope (MIMIC-IV) | Group | n | Mortality, % | CI |
|---|---|---|---|---|
| all 48-h landmark | Improved (<0) | 785 | 28.9 | 25.9-32.2 |
| all 48-h landmark | Unchanged (=0) | 978 | 29.7 | 26.9-32.6 |
| all 48-h landmark | Worsened (>0) | 496 | 37.5 | 33.4-41.8 |
| intermediate 24-h score 4-7 | Improved (<0) | 429 | 24.0 | 20.2-28.3 |
| intermediate 24-h score 4-7 | Unchanged (=0) | 523 | 34.0 | 30.1-38.2 |
| intermediate 24-h score 4-7 | Worsened (>0) | 261 | 43.3 | 37.4-49.4 |

Adjusted odds ratio per one-point 24-to-48-hour increase, adjusted for the
24-hour score: 1.37 (95% CI 1.27-1.47), P < .001.

## Supplementary figures

Figure S1. Cohort derivation flow, including the 24-hour landmark and its
exclusion decomposition, both cohorts; the panel below reports the
death-timing distribution from exact timestamps. Figure S2. Calibration of
CS-MORT-6 at the landmark: internal out-of-fold deciles (both formulations)
and eICU external anion gap, with Wilson 95% confidence intervals per decile.
Figure S3. Decision curves in the landmark common-scorable set: 654
primary-landmark patients (196 deaths, 30.0% mortality) with the five
BOS,MA2 inputs other than mechanical ventilation observed; mechanical
ventilation is treated as absent when unrecorded. The frozen-versus-frozen
comparison is primary; the in-sample recalibrated comparator is shown as a
sensitivity because recalibration favors BOS,MA2 at lower thresholds and not
at higher ones. Figure S4. The integer card drawn:
predicted risk from the score-to-risk mapping (line) and observed landmark
mortality with Wilson 95% confidence intervals (points), from Table S3 panel
C. Figure S5. Within-stage tertile mortality using the arrest-free card (A) and
the four-variable non-staging sub-score (B), MIMIC-IV. For the arrest-free
card, stages B through D equal the primary analysis because the assignment
rules place all recorded arrests in stage E; the sub-score (urine output,
age, blood urea nitrogen, red cell distribution width) uses variables taking
no part in the stage operationalization. Figure S6. Score
trajectory at the 48-hour landmark, symmetric definition: all 48-hour
landmark patients (A) and the intermediate-score subgroup (B). Figure S7.
Subgroup discrimination and calibration at the landmark.

## Figure S1 panel: death timing

| Before ICU | 0 to 6 h | >6 to 12 h | >12 to 24 h | >24 to 48 h | >48 to 168 h | >168 h | No timestamp | Total deaths |
|---|---|---|---|---|---|---|---|---|
| 2 | 73 | 70 | 106 | 157 | 377 | 402 | 1 | 1,188 |

Two records carry death timestamps preceding ICU admission and one death has
no timestamp; all three are retained in mortality counts and identified here
as data anomalies. The 251 landmark exclusions for death comprise the 249
deaths within 24 hours plus the two pre-ICU records; 65.6% of deaths occur
after 48 hours. Of the 539 excluded eICU stays, 431 had shock first
documented after the landmark and 108 were not the patient's first
qualifying stay.
