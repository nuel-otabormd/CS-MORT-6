# CS-MORT-6: Supplementary Material (revision draft)

Supplement to the International Journal of Cardiology Short Communication,
revision of IJCJOURNAL-D-26-03573. Draft for author review; Word formatting
(Times New Roman, three-rule tables, 10 pt italic legends) applied at build.
The revision keeps the submitted tables' titles and layouts, numbered in
order of first citation in the revised manuscript (submitted S6, S7, S8, S9,
and S10 are now S7, S10, S9, S8, and S6); values are updated to the 24-hour
landmark, and additions answer specific reviewer comments. Table S5 and
Table S6 panels A and C reproduce the submitted analysis
(manuscript/CARRIED_FORWARD.md).

## Table S1. TRIPOD+AI reporting checklist.

Abbreviations: CI, confidence interval; PPI, patient and public involvement;
TRIPOD+AI, Transparent Reporting of a multivariable prediction model for
Individual Prognosis Or Diagnosis, artificial intelligence extension.

## Table S2. Variable definitions and measurement windows.

(A) Cohort entry, landmark, and predictors

| Variable | Definition | Units | Time window |
|---|---|---|---|
| Cardiogenic shock (cohort entry) | MIMIC-IV: diagnostic code or affirmed discharge-summary documentation, plus systolic blood pressure <90 mmHg, mean arterial pressure <65 mmHg, lactate ≥2 mmol/L, or vasoactive, inotropic, or mechanical circulatory support; eICU: structured diagnosis. First qualifying ICU stay per patient | - | MIMIC-IV, 0-24 h; eICU, entered by 24 h |
| Landmark population | Alive and in the ICU at 24 h: ICU discharge at or after, and no recorded death at or before, 24 h | - | 24 h |
| Lactate | Most recent lactate | mmol/L | ≤24 h |
| Urine output | First-24h urine / weight / denominator (observed hours capped at 24 in MIMIC-IV; fixed 24-hour denominator in eICU) | mL/kg/h | 0-24 h |
| Cardiac arrest | Cardiac-arrest diagnosis with emergency admission (MIMIC-IV: discharge diagnosis, ICD-10 I46.x or ICD-9 427.5; eICU: structured diagnosis) | Binary | MIMIC-IV, untimed; eICU, by 24 h |
| Age | Age at admission | years | At admission |
| Blood urea nitrogen | Most recent BUN | mg/dL | ≤24 h |
| Red cell distribution width | Most recent RDW | % | ≤24 h |
| Anion gap | Sodium − (chloride + bicarbonate), each the most recent value | mmol/L | ≤24 h |

Abbreviations: BUN, blood urea nitrogen; RDW, red cell distribution width.
The 48-hour reassessment applies the same definitions over 48 hours. In
eICU, arrest diagnoses first documented after the landmark are set to absent.

(B) EHR-derived SCAI stage rules (MIMIC-IV, first 24 hours)

| Stage | Rule |
|---|---|
| E | Cardiac arrest, ≥3 vasoactive agents (vasopressor count plus inotrope use), or ≥2 mechanical circulatory support devices |
| D | 2 vasoactive agents, any device, or maximum lactate > 4 mmol/L on ≥1 vasoactive agent |
| C | ≥1 vasoactive agent, or maximum lactate ≥2 mmol/L with hypotension (minimum systolic < 90 or minimum mean < 65 mmHg) |
| B | Hypotension or maximum lactate ≥2 mmol/L |
| A | Otherwise |

Rules apply in the order E, D, C, B; the first matching rule assigns the
stage. In eICU, stage E is any recorded cardiac-arrest diagnosis, D any
recorded mechanical support interface, C any vasopressor or inotrope, and B
otherwise; stage A is not assignable because all cohort members meet the
shock definition. The eICU stage-E rule accepts any recorded arrest diagnosis
without the emergency-admission restriction of the score's arrest predictor,
so 238 of 1,047 primary-landmark patients are staged E while 147 carry the
arrest point.

## Table S3. Model specification and integer scoring.

(A) Continuous model specification for third-party use

| Variable | Winsor (1st-99th) | Median | Mean | SD | β, lactate model | β, anion-gap model |
|---|---|---|---|---|---|---|
| Lactate (mmol/L) | 0.7-12.723 | 1.9 | 2.418 | 1.8608 | +0.496888 | NA |
| Anion gap (mmol/L) | 5.0-29.0 | 13.0 | 13.3935 | 4.5533 | NA | +0.427884 |
| Urine output (mL/kg/h) | 0.0013-3.8352 | 0.728 | 0.9197 | 0.7526 | -0.427892 | -0.463905 |
| Cardiac arrest (0/1) | 0-1 | 0.0 | 0.095 | 0.2933 | +0.325232 | +0.361791 |
| Age (years) | 27.93-93.0 | 71.0 | 69.6641 | 14.0336 | +0.263458 | +0.271008 |
| Blood urea nitrogen (mg/dL) | 8.0-122.16 | 33.0 | 39.2072 | 24.9254 | +0.254663 | +0.082329 |
| Red cell distribution width (%) | 12.2-24.496 | 15.2 | 15.7704 | 2.4865 | +0.198363 | +0.186597 |
| Intercept | | | | | -0.806673 | -0.82333 |

Abbreviations: SD, standard deviation. Coefficients were estimated at the
24-hour landmark and apply to standardized values: predicted probability = 1
/ (1 + exp(-(intercept + sum of β × z))), with z = (value - mean) / SD after
winsorization and median imputation. The anion-gap model is fitted
separately, with anion gap in place of lactate.

(B) CS-MORT-6 integer scoring system

| Variable | Category | Points |
|---|---|---|
| Lactate (mmol/L) | <2 / 2 to <4 / ≥4 | 0 / 2 / 4 |
| Urine output (mL/kg/h) | ≥1 / 0.5 to <1 / <0.5 | 0 / 1 / 2 |
| Cardiac arrest | No / Yes | 0 / 3 |
| Age (years) | <65 / 65 to <80 / ≥80 | 0 / 1 / 2 |
| Blood urea nitrogen (mg/dL) | <25 / 25 to <45 / ≥45 | 0 / 1 / 2 |
| Red cell distribution width (%) | <14.5 / 14.5 to <16 / ≥16 | 0 / 1 / 2 |

Total score 0 to 15. Where lactate is unavailable, the anion gap (from
sodium, chloride, and bicarbonate) substitutes, scored <12 / 12 to <18 / ≥18
as 0 / 2 / 4, and scores 2 when also unavailable; this rule applied at
external validation, whereas in the development cohort a missing lactate
scored 0. Other missing components score the category of their development
median (panel A): 1 point each for urine output, age, blood urea nitrogen,
and red cell distribution width. An absent arrest record scores 0.

## Table S4. Model development.

(A) Model-class comparison

| Model | AUROC | Calibration slope |
|---|---|---|
| Ridge-penalized logistic regression (selected) | 0.792 | 0.93 |
| LASSO logistic | 0.792 | 0.95 |
| Random forest | 0.790 | 1.61 |
| Gradient boosting | 0.796 | 0.75 |

Abbreviations: AUROC, area under the receiver operating characteristic curve;
LASSO, least absolute shrinkage and selection operator. The comparison used a
wider candidate pool than the final six-variable model, so its values differ
from the final model's.

(B) Sample size and predictor screen

| Analysis | Result |
|---|---|
| Minimum sample size, six fixed predictors at the landmark (Riley et al; C-statistic 0.70, outcome proportion 0.331) | 469 patients, 156 events |
| Predictor screen: candidate parameters; ICU stays (patients); deaths | 58; 4,315 (3,192); 1,537 |
| Parameters selected in ≥80% of 400 bootstrap resamples (L1-penalized logistic regression) | 38 |
| Retained predictors selected in all 400 resamples | 5 of 6 (blood urea nitrogen, 399 of 400) |

Parameters requiring imaging, neurological assessment, treatment-dependent
measurement, or additional hemodynamic information were not carried into a
bedside score.

(C) Nested redevelopment

| Pool | Candidates | Redeveloped AUROC | Paired difference (95% CI) |
|---|---|---|---|
| Deployable: harmonized definitions, ≥80% availability in both databases | 13 | 0.718 | -0.014 (-0.029 to +0.001) |
| Symmetric: lactate and urine output restored | 15 | 0.725 | -0.007 (-0.020 to +0.005) |

Selection was repeated within each fold of 10-times-repeated 5-fold
cross-validation; differences are versus the six-variable model (AUROC 0.733)
on the same folds. Age, cardiac arrest, and red cell distribution width were
reselected in every fold of both pools, and blood urea nitrogen in 76%
(deployable) and 98% (symmetric). Lactate (38%) and urine output (6%) were
rarely reselected in the symmetric pool, a limitation; they were retained on
their original selection, as neither redevelopment performed better.

## Table S5. Baseline characteristics of the derivation and validation cohorts.

(A) MIMIC-IV derivation cohort

Values are median (IQR) or n (%), within 24 hours. SCAI stages A and B (472
patients) not tabulated.

(B) eICU external validation cohort

Abbreviations: eICU, eICU Collaborative Research Database; IQR, interquartile
range. Both panels describe the full cohorts from which the 24-hour landmark
populations are drawn (Figure S1).

## Table S6. Missing data, imputation, and collinearity.

(A) Missing-data analysis (MIMIC-IV)

| Variable | Missing | Mortality if missing | Mortality if measured | Pattern |
|---|---|---|---|---|
| Lactate | 19.4% | 28.7% | 40.6% | Consistent with MNAR: lower mortality when missing |
| Urine output | 8.3% | 56.2% | 36.7% | Consistent with MNAR: higher mortality when missing |

Abbreviations: MNAR, missing not at random. Full development cohort
(n=3,103), submitted analysis.

(B) Imputation sensitivity

| Imputation | Continuous AUROC | Slope | CITL |
|---|---|---|---|
| Median (analytic default) | 0.734 | 0.99 | -0.00 |
| Chained equations (single imputation within folds) | 0.725 | 1.01 | +0.00 |

Abbreviations: CITL, calibration-in-the-large. Landmark population, lactate
formulation, out-of-fold; the chained-equations imputation was fitted within
each training fold without multiple-imputation pooling.

(C) SCAI stage completeness

| SCAI stage | n | In-hospital mortality |
|---|---|---|
| A | 8 | 0.0% |
| B | 464 | 25.6% |

Panel C reports SCAI stage completeness in the MIMIC-IV derivation cohort;
stages A and B (472 patients) complete the stage distribution alongside
stages C, D, and E reported in Supplementary Table S5.

(D) Collinearity: variance inflation factors for every predictor

| Predictor | Lactate model | Anion-gap model |
|---|---|---|
| Lactate / anion gap | 1.05 | 1.22 |
| Urine output | 1.08 | 1.06 |
| Cardiac arrest | 1.02 | 1.01 |
| Age | 1.08 | 1.08 |
| Blood urea nitrogen | 1.16 | 1.31 |
| Red cell distribution width | 1.10 | 1.11 |

MIMIC-IV landmark population, on the winsorized, imputed, standardized
design. Correlations were 0.00 for lactate and blood urea nitrogen, 0.06 for
lactate and red cell distribution width, and 0.28 for blood urea nitrogen
and red cell distribution width; the largest in either formulation is anion
gap with blood urea nitrogen at 0.37.

(E) Observed-data availability, % of patients

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
patients in the ICU at each whole-hour boundary, n=2,731 at 24 hours).
Availability is observed data; after the missing-value rules (Table S3)
every patient is evaluable.

## Table S7. Score behavior across thresholds and risk categories.

(A) Diagnostic accuracy at integer score thresholds

| Threshold | Sensitivity | Specificity | PPV | NPV | LR+ | LR− |
|---|---|---|---|---|---|---|
| ≥4 | 0.89 | 0.37 | 0.41 | 0.87 | 1.41 | 0.29 |
| ≥6 | 0.65 | 0.67 | 0.50 | 0.80 | 2.00 | 0.52 |
| ≥8 | 0.36 | 0.89 | 0.62 | 0.74 | 3.32 | 0.72 |
| ≥9 | 0.24 | 0.94 | 0.67 | 0.71 | 4.14 | 0.81 |

Abbreviations: LR+, positive likelihood ratio; LR−, negative likelihood ratio;
NPV, negative predictive value; PPV, positive predictive value. MIMIC-IV
landmark population, out-of-fold.

(B) Risk stratification by score category

| Risk category | Score | MIMIC-IV mortality | eICU (lactate) | eICU (anion gap) |
|---|---|---|---|---|
| Low | 0-3 | 12.7% | 8.8% | 10.3% |
| Moderate | 4-5 | 27.9% | 18.8% | 20.6% |
| High | 6-7 | 40.1% | 39.6% | 43.0% |
| Very High | 8-15 | 62.2% | 59.3% | 58.3% |

Abbreviations: eICU, eICU Collaborative Research Database; MIMIC-IV, Medical
Information Mart for Intensive Care IV. Landmark populations. The eICU lactate column follows the external rule,
lactate categories when measured and anion-gap categories otherwise
(mapped-risk calibration slope 1.15, calibration-in-the-large -0.22); the
anion-gap column uses anion-gap categories for every patient (AUROC 0.738,
versus 0.759 under the external rule). Rescoring the development cohort under the
external rule (anion-gap bands for the 19.2% without an observed lactate)
gives AUROC 0.720, versus 0.727 under the development rule.

## Table S8. Sensitivity and subgroup analyses.

(A) Sensitivity across cohort definitions

| Analysis | N | Mortality | Continuous AUROC | Integer AUROC |
|---|---|---|---|---|
| Primary landmark population | 2,694 | 33.1% | 0.734 | 0.727 |
| Sensitivity: ICD-confirmed only | 2,452 | 33.2% | 0.734 | 0.727 |
| Sensitivity: Sepsis-3 excluded | 1,321 | 28.2% | 0.747 | 0.739 |
| Sensitivity: cardiac arrest removed from the score | 2,694 | 33.1% | NA | 0.711 |
| Subgroup: patients without cardiac arrest | 2,438 | 30.8% | 0.724 | 0.712 |

Abbreviations: AUROC, area under the receiver operating characteristic curve.
Out-of-fold point estimates for the lactate formulation and the integer score.

(B) Subgroup discrimination and calibration

| Subgroup | n | Deaths | Mortality | AUROC (95% CI) | Slope | CITL |
|---|---|---|---|---|---|---|
| Male | 1,629 | 519 | 31.9% | 0.748 (0.724-0.774) | 1.07 | -0.06 |
| Female | 1,065 | 373 | 35.0% | 0.713 (0.682-0.746) | 0.89 | +0.09 |
| White | 1,687 | 537 | 31.8% | 0.732 (0.706-0.757) | 1.03 | -0.07 |
| Black | 267 | 80 | 30.0% | 0.704 (0.631-0.771) | 0.81 | -0.30 |
| Hispanic | 80 | 24 | 30.0% | 0.805 (0.692-0.903) | 1.21 | -0.11 |
| Asian | 67 | 17 | 25.4% | 0.708 (0.548-0.851) | 0.68 | -0.37 |
| Other/Unknown | 593 | 234 | 39.5% | 0.754 (0.715-0.792) | 1.07 | +0.36 |

Abbreviations: AUROC, area under the receiver operating characteristic curve;
CI, confidence interval; CITL, calibration-in-the-large. Landmark population,
lactate formulation, out-of-fold. Recorded race is a social classification;
Other/Unknown is heterogeneous (in the full cohort, 119 Other and 574 Unknown
or declined). Estimates for the Hispanic and Asian groups were imprecise
because of small sample sizes.

(C) Cluster heterogeneity across eICU hospitals

| Hospitals (≥25 CS patients) | Median AUROC | IQR | Range | Pooled eICU AUROC |
|---|---|---|---|---|
| 12 | 0.766 | 0.678-0.779 | 0.632-1.000 | 0.748 |

Abbreviations: AUROC, area under the receiver operating characteristic curve;
CS, cardiogenic shock; IQR, interquartile range. Primary external landmark
population (1,047 patients, 117 hospitals), anion-gap model; the 12 hospitals
contributed 479 patients.

(D) All-admissions performance, retained for comparability with existing scores

| Metric | MIMIC-IV (n=3,103) | eICU (1,866 stays; 132 hospitals) |
|---|---|---|
| Continuous, lactate | 0.778 (0.760-0.794) | 0.757 (0.735-0.780) |
| Continuous, anion gap | 0.762 (0.744-0.779) | 0.749 (0.726-0.772) |
| Integer card | 0.758 (0.740-0.774) | 0.732 (0.709-0.755) |
| Calibration | out-of-fold slope 0.98 (lactate formulation) | anion gap slope 0.96, CITL +0.04 |
| BOS,MA2 head-to-head (n=1,127) | - | 0.749 vs 0.743; diff +0.006 (-0.026 to +0.037) |

Day-1 frame, repeat stays included. As in Table 1, the integer card is
scored under each cohort's missing-component rule (Table S3).

## Table S9. Within-stage score-tertile mortality with cell sizes and 95% confidence intervals.

(A) Within-stage tertile mortality, 24-hour landmark

| SCAI stage | Cohort | Low tertile | Middle tertile | High tertile |
|---|---|---|---|---|
| B | MIMIC-IV | 16.1% (11.3-22.4)<br>n = 168 | 29.6% (22.6-37.8)<br>n = 135 | 36.5% (27.9-46.1)<br>n = 104 |
|   | eICU | 7.0% (3.7-12.7)<br>n = 129 | 27.5% (18.4-39.0)<br>n = 69 | 36.4% (25.8-48.4)<br>n = 66 |
| C | MIMIC-IV | 16.0% (12.8-19.8)<br>n = 419 | 35.4% (29.8-41.4)<br>n = 257 | 45.9% (39.6-52.3)<br>n = 233 |
|   | eICU | 11.6% (7.6-17.2)<br>n = 173 | 28.7% (21.0-37.9)<br>n = 108 | 53.5% (43.8-63.0)<br>n = 99 |
| D | MIMIC-IV | 13.2% (9.9-17.5)<br>n = 310 | 26.7% (21.1-33.2)<br>n = 202 | 57.8% (50.6-64.6)<br>n = 187 |
|   | eICU | 8.2% (3.8-16.8)<br>n = 73 | 15.9% (7.9-29.4)<br>n = 44 | 45.8% (32.6-59.7)<br>n = 48 |
| E | MIMIC-IV | 26.7% (21.5-32.7)<br>n = 236 | 49.2% (43.2-55.3)<br>n = 262 | 73.4% (66.4-79.4)<br>n = 173 |
|   | eICU | 33.0% (24.8-42.4)<br>n = 106 | 54.2% (41.7-66.3)<br>n = 59 | 64.4% (52.9-74.4)<br>n = 73 |

Abbreviations: CI, confidence interval; eICU, eICU Collaborative Research Database; MIMIC-IV, Medical Information Mart for Intensive Care IV; SCAI, Society for Cardiovascular Angiography and Interventions. Each cell gives in-hospital mortality (95% CI) and the number of patients. Tied integer values make tertile sizes unequal. Stage A (n=8, no deaths) is not
tabulated; these eight patients met the cohort hypoperfusion criterion
through measurements outside the staging component set (seven had no
lactate in the staging window), so absent components under-stage them.

(B) Incremental value

| Cohort | Formulation | Stage only | Score only | Stage + score | Difference (95% CI) |
|---|---|---|---|---|---|
| MIMIC-IV | Integer card | 0.589 | 0.727 | 0.728 | +0.139 (+0.116 to +0.163) |
| MIMIC-IV | Continuous anion gap | 0.589 | 0.726 | 0.728 | +0.139 (+0.116 to +0.162) |
| eICU | Continuous anion gap | 0.613 | 0.748 | 0.754 | +0.141 (+0.101 to +0.178) |
| eICU | Integer card | 0.613 | 0.759 | 0.767 | +0.154 (+0.116 to +0.191) |

Intervals are paired bootstrap percentiles; likelihood-ratio tests for the
score over the stage gave P < .001 in every row. With the stage entered as
separate categories rather than one ordered term, the increments were +0.140
and +0.142 in MIMIC-IV and +0.125 and +0.135 in eICU (continuous and integer
formulations).

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

## Table S10. Head-to-head comparison with existing scores in eICU.

(A) Primary external population

| Score | Scorable | AUROC (95% CI) | Calibration slope / CITL |
|---|---|---|---|
| CS-MORT-6 (anion gap) | 53.3% all six observed / 96.4% anion gap observed / 100% evaluable after missing-value rules | 0.748 (0.715-0.780) | 1.17 / -0.001 |
| CS-MORT-6 (lactate) | 29.5% all six observed / 52.5% lactate observed / 100% evaluable after missing-value rules | 0.759 (0.728-0.789) | 1.08 / -0.251 |
| BOS,MA2 | 654 of 1,047 with complete checklist | 0.751 | NA |

Abbreviations: AUROC, area under the receiver operating characteristic curve;
CI, confidence interval; CITL, calibration-in-the-large. In the 654 patients
(196 deaths) scorable by both models, CS-MORT-6 (anion gap) reached 0.755,
a difference of +0.004 (95% CI -0.039 to +0.046). With missing BOS,MA2
components imputed by chained equations, not a replication of its
development study's predictive-mean-matching, BOS,MA2 reached 0.735 in all
1,047 patients (difference +0.014, -0.024 to +0.050).

(B) External landmark populations (frozen model unchanged)

| Population | n | Deaths | Anion-gap AUROC | Deployment-rule card | Anion-gap-bands card |
|---|---|---|---|---|---|
| Primary: one stay/patient, shock documented by 24 h | 1,047 | 305 | 0.748 (0.715-0.780) | 0.759 (0.729-0.790) | 0.738 (0.707-0.770) |
| One stay/patient, any-time documentation | 1,439 | 453 | 0.716 (0.688-0.745) | - | 0.702 (0.674-0.731) |
| All landmark stays | 1,586 | 478 | 0.713 (0.685-0.739) | - | 0.697 (0.669-0.724) |

The 1,586 landmark stays comprise 1,439 unique patients (147 repeat stays);
late-documented eligibility and repeat stays each attenuated discrimination.
Retaining the five arrest flags first documented after 24 hours gives anion
gap 0.747 and deployment-rule card 0.758.

## Table S11. 48-hour reassessment and score trajectory.

(A) The 24-hour model applied again at 48 hours

| Cohort (formulation) | n | Deaths | AUROC, reassessed at 48 h (95% CI) | Slope | CITL | AUROC, 24-h prediction | Difference (95% CI) |
|---|---|---|---|---|---|---|---|
| MIMIC-IV (lactate) | 2,259 | 703 | 0.739 (0.717-0.760) | 1.10 | +0.03 | 0.714 | +0.024 (+0.012 to +0.036) |
| eICU (anion gap) | 806 | 202 | 0.725 (0.685-0.765) | 1.07 | -0.14 | 0.716 | +0.009 (-0.012 to +0.030) |

Abbreviations: AUROC, area under the receiver operating characteristic
curve; CITL, calibration-in-the-large. Patients alive and in the ICU at 48
hours; eICU primary external population. Slope and CITL describe the
reassessed predictions; for the 24-hour prediction in eICU they were 0.99 and
-0.20.

(B) Score change from 24 to 48 hours (Figure S6)

| Patients (MIMIC-IV) | Score change | n | Mortality, % | 95% CI |
|---|---|---|---|---|
| All at 48 h | Improved | 785 | 28.9 | 25.9-32.2 |
|   | Unchanged | 978 | 29.7 | 26.9-32.6 |
|   | Worsened | 496 | 37.5 | 33.4-41.8 |
| 24-h score 4 to 7 | Improved | 429 | 24.0 | 20.2-28.3 |
|   | Unchanged | 523 | 34.0 | 30.1-38.2 |
|   | Worsened | 261 | 43.3 | 37.4-49.4 |

Improved, score decreased; worsened, score increased. Odds ratio for death
per 1-point increase from 24 to 48 hours, adjusted for the 24-hour score:
1.37 (95% CI 1.27-1.47), P < .001.

## Supplementary figures

### Figure S1. Cohort derivation flow diagram.

Derivation of the MIMIC-IV development cohort and the eICU external
validation cohort, including the 24-hour landmark and its exclusions (A), and
the timing of the 1,188 in-hospital deaths of the development cohort from
exact timestamps (B), where the bars count deaths within intervals of unequal
length and the line gives the cumulative share. Two deaths
carry timestamps preceding ICU admission and one has no timestamp; all three
are retained in mortality counts and are not plotted. The 251 landmark
exclusions for death comprise the 249 deaths within 24 hours plus the two
pre-ICU records, and 65.6% of deaths occur after 48 hours. Of the 539
excluded eICU stays, 431 had shock first documented after the landmark and
108 were not the patient's first qualifying stay. Day-1 all-admissions
analyses use the 1,866-stay cohort; the 1,586-stay and 1,439-patient
populations are reported as sensitivity analyses.

### Figure S2. Calibration of CS-MORT-6.

Calibration at the landmark: internal out-of-fold deciles (both formulations)
and eICU external anion gap, with Wilson 95% confidence intervals per decile.

### Figure S3. Decision-curve analysis.

Decision curves in the landmark common-scorable set: 654 primary-landmark
patients (196 deaths, 30.0% mortality) with the five BOS,MA2 inputs other
than mechanical ventilation observed; mechanical ventilation is treated as
absent when unrecorded. The frozen-versus-frozen comparison is primary; the
in-sample recalibrated comparator is shown as a sensitivity because
recalibration favors BOS,MA2 at lower thresholds and not at higher ones.

### Figure S4. Predicted and observed mortality by integer score.

Predicted risk by score (line) and observed landmark mortality with Wilson
95% confidence intervals (points).

### Figure S5. Within-stage risk resolution using the arrest-free score and variables absent from the staging.

Within-stage tertile mortality using the arrest-free card (A) and the
four-variable non-staging sub-score (B), MIMIC-IV. For the arrest-free card,
stages B through D equal the primary analysis because the assignment rules
place all recorded arrests in stage E; the sub-score (urine output, age,
blood urea nitrogen, red cell distribution width) uses variables taking no
part in the stage operationalization.

### Figure S6. Score trajectory and mortality.

In-hospital mortality by score change from 24 to 48 hours, with any decrease
counted as improved and any increase as worsened: all patients at the
48-hour landmark (A) and those with a 24-hour score of 4 to 7 (B).

### Figure S7. Subgroup discrimination and calibration.

(A) Subgroup area under the receiver operating characteristic curve with 95%
confidence intervals; point size reflects the number of deaths. (B)
Calibration-in-the-large by subgroup. Landmark population, lactate
formulation.
