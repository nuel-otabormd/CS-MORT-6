# Revised manuscript draft (IJCJOURNAL-D-26-03573, revision 1)

Draft for author review before Word build. Every number traces to
CONSOLIDATED_RESULTS_20260907.md; the complete package (pipeline, outputs,
ledger, manuscript, supplement) is checksummed together at the repository
release. House style applied: no
em-dashes, no bullets in prose, percentages to one decimal, AMA P values.
Reference changes at the end. Word-count convention (recorded for
reproducibility): the 1,500-word limit covers the prose of sections 1-5
only, excluding title page, highlights, abstract, keywords, Table 1, figure
legend, declarations, and references; identical to the submitted package's
counting span.

---

## Title

CS-MORT-6: A Mortality Score That Refines Risk Within EHR-Derived SCAI Stages in Cardiogenic Shock

## Highlights

A six-variable integer score refines risk within EHR-derived SCAI stages.
At 24 hours, external integer-score AUROC was 0.759 across 117 hospitals.
Within-stage mortality differed by 20 to 47 percentage points.
Discrimination was similar to BOS,MA2 among patients scorable by both models.
Repeated scoring and real-time use require prospective evaluation.

## Abstract

Background: Cardiogenic shock carries high in-hospital mortality, and the
ordinal SCAI classification does not quantify differences in risk among
patients assigned to the same stage. Existing scores generally require
imaging, procedural, or support-dependent data.

Methods: We identified 3,103 adults with documented cardiogenic shock in
MIMIC-IV. The primary outcome was in-hospital death after 24 hours among
patients alive and still in the ICU at that time (n=2,694; 892 deaths).
CS-MORT-6 is a 0-to-15-point score using lactate or anion gap, urine output,
cardiac arrest, age, blood urea nitrogen, and red cell distribution width. The
frozen model was applied to an external-validation cohort of 1,047 patients
across 117 eICU hospitals.

Results: For predicting in-hospital death after 24 hours, internal
cross-validated AUROC was 0.734 (95% CI, 0.714-0.754) for the lactate model
and 0.726 (0.707-0.746) for the anion-gap model. External AUROC was 0.748
(0.715-0.780) for the anion-gap model, with calibration-in-the-large 0.00, and
0.759 (0.729-0.790) for the integer score. Mortality differed by 20 to 47
percentage points between the lowest and highest score tertiles within
EHR-derived SCAI stages. In within-cohort analyses, adding the continuous
anion-gap score to SCAI stage increased AUROC by 0.139 (0.116-0.162) in
MIMIC-IV and 0.141 (0.101-0.178) in eICU, whereas adding stage to the score
moved AUROC only from 0.726 to 0.728. The AUROC difference from BOS,MA2 was
0.004 (-0.039 to 0.046).

Conclusions: At 24 hours, CS-MORT-6 distinguished mortality risk among
patients assigned to the same EHR-derived SCAI stage and retained moderate
discrimination during external validation. Repeated scoring
and real-time performance require prospective evaluation.

Keywords: cardiogenic shock; risk score; SCAI stage; landmark analysis; external validation; mortality

---

## 1. Introduction

Cardiogenic shock remains among the most lethal conditions in cardiovascular
medicine, with in-hospital mortality of 30% to 50% despite advances in
revascularization, mechanical circulatory support (MCS), and systems of care
[1]. Early risk stratification guides escalation to advanced therapies,
transfer within regionalized networks, and goals-of-care discussions. The
Society for Cardiovascular Angiography and Interventions (SCAI) shock
classification provides an ordinal framework for communicating shock severity
and stratifying mortality risk across five stages [2,3]. However,
heterogeneity in mortality risk persists among patients assigned to the same
stage [4].

Existing quantitative scores each carry a practical constraint. CardShock
requires echocardiographic ejection fraction [5], IABP-SHOCK II requires
post-procedural coronary flow [6], and BOS,MA2 uses support-dependent vital
signs [7]. Serial SCAI assessment and machine-learning phenotypes have also
been evaluated in specialized registries [8,9]. We developed CS-MORT-6 to
quantify mortality risk among patients assigned to the same electronic health
record (EHR)-derived SCAI stage, and evaluated its performance at 24 hours,
after completion of the score's measurement window.

## 2. Methods

We used MIMIC-IV (Beth Israel Deaconess Medical Center, 2008-2022) for
development and the eICU Collaborative Research Database (208 hospitals,
2014-2015) for external validation [10,11]. Reporting followed TRIPOD+AI [12]
(checklist, Supplementary Table S1). Adults aged ≥18 years with cardiogenic
shock were identified in MIMIC-IV by a documentation-anchored phenotype
(diagnostic code or affirmed discharge-summary documentation) plus at least
one physiological or support criterion within 24 hours (systolic blood
pressure <90 mmHg, mean arterial pressure <65 mmHg, lactate ≥2 mmol/L, or
vasoactive, inotropic, or mechanical circulatory support). MIMIC-IV case
identification used the completed hospitalization. In eICU, we required a
structured diagnosis entered by 24 hours and retained the first qualifying ICU
stay per patient. Primary analyses used a 24-hour landmark after ICU admission
among patients alive and still in the ICU [13], with subsequent in-hospital
mortality as the primary outcome. Supplementary Table S2 details phenotype,
cohort, and variable definitions.

Laboratory predictors used the most recent value up to 24 hours rather than
the worst. We compared penalized logistic regression (ridge and LASSO), random
forests, and gradient boosting, and adopted ridge regression for calibration
stability and the transparent integer score it enables. Six predictors
(lactate, urine output, cardiac arrest, age, blood urea nitrogen, and red cell
distribution width) were chosen by bootstrap stability selection with
L1-penalized logistic regression and clinical review, then held fixed for
coefficient and intercept re-estimation at 24 hours using L2 penalization
(C=0.5, untuned). Sample-size calculations addressed the fixed model and
predictor screen [14] (Supplementary Table S2). The original 0-to-15 integer
score based on the approach of Sullivan and colleagues [15] was retained, with
re-estimation of its score-to-risk mapping (Supplementary Tables S3 and S4).
Because lactate was incompletely observed, a separate continuous model
replaced lactate with harmonized anion gap, retaining the other five
predictors. The integer score was therefore scored differently in the two
cohorts: externally it used lactate categories when available and anion-gap
categories otherwise, whereas internally a missing component took its
development-median category (Supplementary Tables S2 and S4).

Discrimination was summarized by the area under the receiver operating
characteristic curve (AUROC). Internal validation used five-fold
cross-validation with preprocessing within folds. CIs used influence-function
estimation for continuous models [16] and patient-level bootstrap of
out-of-fold integer scores (Table 1). Calibration used the calibration slope,
calibration-in-the-large (CITL), and the Brier score. Clinical utility was
assessed by decision-curve analysis. Correlations and variance inflation
factors assessed collinearity. For external validation, continuous models and
risk mapping were fixed on the development data and applied unchanged to eICU,
with comparison against BOS,MA2 by the DeLong method [7,17].

EHR-derived SCAI stages were operationalized from blood pressure, lactate,
therapies, device support, and cardiac arrest using adapted consensus rules
[2-4] (Supplementary Table S2). Within-stage stratification used score
tertiles within each stage and cohort. Incremental discrimination was assessed
by likelihood-ratio testing and paired bootstrap. Increments are apparent
within-cohort estimates: the combined models were fitted and evaluated in the
same cohort. Exploratory analyses reapplied the 24-hour model at 48 hours
among patients alive and still in the ICU, without fitting a separate 48-hour
model. Analyses used Python 3.9 and R with a fixed random seed.

## 3. Results

Of 3,103 MIMIC-IV patients with cardiogenic shock, 1,188 died in hospital
(38.3%). Of these deaths, 249 occurred within 24 hours and 779 (65.6%) after
48 hours (Supplementary Tables S5 and S6). The primary 24-hour population
included 2,694 patients with 892 subsequent deaths (33.1%), exceeding the
156-event minimum. The primary eICU population included 1,047 patients with
305 deaths (29.1%) across 117 hospitals. In eICU, availability was 96.4% for
anion gap, 60.6% for urine output, and 52.5% for lactate. All anion-gap-model
inputs were observed in 53.3% (Supplementary Table S7). All variance
inflation factors were ≤1.31 (Supplementary Table S8).

Internal cross-validated AUROCs were 0.734 for the continuous lactate model,
0.726 for the anion-gap model, and 0.727 for the integer score. Externally the
anion-gap model reached 0.748 and the other two 0.759 (Table 1). Mortality by
score band is reported in Supplementary Table S9. In MIMIC-IV, including
patients who died or left the ICU before 24 hours yielded an AUROC of 0.778
for the lactate model (Supplementary Table S10). In fully nested
cross-validation, redevelopment from broader candidate pools did not improve
on the fixed six-variable model (Supplementary Table S11).

Within EHR-derived SCAI stages, mortality differed by 20 to 47 percentage
points between the lowest and highest CS-MORT-6 tertiles in MIMIC-IV, with a
similar pattern in eICU (Figure 1 and Supplementary Table S12). Applying the
MIMIC-IV cutpoints unchanged to eICU, rather than eICU's own tertiles,
produced monotonically rising mortality across score groups in every stage.
Adding the continuous anion-gap model to SCAI stage increased AUROC from 0.589
to 0.728 in MIMIC-IV and from 0.613 to 0.754 in eICU. Adding stage to the
anion-gap model changed AUROC from 0.726 to 0.728 in MIMIC-IV and from 0.748
to 0.754 in eICU.

In MIMIC-IV, mortality differences between CS-MORT-6 tertiles within SCAI
stages persisted when cardiac arrest was removed from the score and when the
score was restricted to four predictors not used to assign SCAI stage. In both
cohorts, the continuous anion-gap model still increased AUROC over SCAI stage
alone when cardiac arrest was excluded from the rules used to assign stage.
The gain also remained when stages were entered as separate categories,
allowing each stage its own association with mortality (Supplementary Table
S12).

Among 654 eICU patients scorable with both models, the AUROC difference
between the continuous anion-gap model and BOS,MA2 was 0.004 (95% CI, -0.039
to 0.046). CardShock and IABP-SHOCK II could not be calculated in eICU [5,6].
In broader eICU populations without the 24-hour documentation restriction,
anion-gap-model AUROCs were 0.713 to 0.716 (Supplementary Table S10).

In MIMIC-IV, subgroup AUROCs for the lactate formulation ranged from 0.70 to
0.81. CITL was -0.37 among Asian patients, -0.30 among Black patients, and
0.36 in the Other or Unknown group (Supplementary Table S13).

Among patients eligible at 48 hours, exploratory reassessment changed AUROC by
0.024 (95% CI, 0.012-0.036) in MIMIC-IV and 0.009 (-0.012 to 0.030) in eICU
compared with the 24-hour assessment (Supplementary Table S14).

## 4. Discussion

SCAI staging standardizes how the severity of shock is described, but it does
not rank risk among patients within a stage. CS-MORT-6 ranked risk within
stages in MIMIC-IV, and its cutpoints transported unchanged to eICU. Registry
studies have pursued similar refinement through repeated assessment and
machine-learning phenotypes [8,9], though in a multicentre registry rather
than in routine electronic records. The limited gain from adding EHR-derived
stage to the anion-gap model may partly reflect their overlapping
cardiac-arrest information, and does not imply that stage carries no
prognostic information.

CS-MORT-6 uses six variables and requires no imaging or procedural findings.
Discrimination was moderate. Among patients scorable with both models, the
difference in AUROC between the continuous anion-gap model and BOS,MA2 was
small, but its confidence interval did not establish equivalence or
superiority. The two scores share three of six variables: age, blood urea
nitrogen, and anion gap [7]. In eICU the anion-gap model had no average
calibration offset, although its slope of 1.17 indicates that predicted risks
were insufficiently spread on the log-odds scale, and the integer score
over-predicted on average.

Calibration varied across subgroups, including by race, and the smallest
groups were imprecisely estimated. We did not recalibrate within those groups.
Matching the score to each group's observed mortality would carry forward any
part of those differences that reflects care rather than severity of illness
[18]. Nor did we impose fairness constraints, which can reduce within-group
performance without consistently improving calibration [19]. Because equal
calibration and equal error rates cannot both hold when outcome rates differ
between groups [20], we report subgroup performance rather than adjust it, and
recommend local evaluation before clinical use.

Reapplying the 24-hour model at 48 hours improved discrimination internally,
but the external difference remained uncertain, so serial validity is not
established. The association between score change and subsequent death is a
monitoring observation rather than a validated dynamic prediction model.
CS-MORT-6 is a stratification tool rather than a treatment determinant, and
whether embedding it in a decision-support workflow improves outcomes requires
prospective evaluation.

### 4.1. Study limitations

Case identification relied on documented recognition of cardiogenic shock, so
performance cannot be assumed in early or unrecognized presentations.
Development was single-center, though external validation spanned 117
hospitals. Predictors were selected before landmark cross-validation, so the
internal-validation intervals do not account for selection uncertainty.

In MIMIC-IV the arrest diagnosis was untimed and could have been recorded
after the landmark, so a predictor may carry information from after the
assessment time. Performance using only information available in real time at
24 hours is therefore not established, and early emergency-department use and
the effect of documentation delay were not evaluated.

Because eICU contributed to BOS,MA2 development and informed some analytic
choices in the present study, the external validation was not fully
independent. Confirmation in an untouched cohort is needed.

## 5. Conclusions

At 24 hours, CS-MORT-6 distinguished mortality risk among patients assigned to
the same EHR-derived SCAI stage in both cohorts, with moderate discrimination.
Its value lies in quantifying risk within an EHR-derived SCAI stage rather
than replacing SCAI classification. Prospective evaluation should establish
performance using real-time inputs and repeated assessment.

---

## Table 1. Performance at 24 hours

| Metric | MIMIC-IV development | eICU external validation |
|---|---|---|
| n / deaths / mortality | 2,694 / 892 / 33.1% | 1,047 / 305 / 29.1% |
| Continuous lactate AUROC | 0.734 (0.714-0.754) | 0.759 (0.728-0.789) |
| Continuous anion-gap AUROC | 0.726 (0.707-0.746) | 0.748 (0.715-0.780) |
| Integer score AUROC | 0.727 (0.706-0.747) | 0.759 (0.729-0.790) |
| Calibration slope / CITL, lactate formulation | 0.99 / 0.00, out of fold | 1.08 / -0.25 |
| Calibration slope / CITL, anion-gap formulation | 0.99 / 0.00, out of fold | 1.17 / 0.00 |
| Calibration slope / CITL, integer score | - | 1.15 / -0.22 |
| Brier score, anion-gap formulation | 0.189, out of fold | 0.172 |
| Incremental AUROC over EHR-derived stage, continuous anion-gap formulation | 0.139 (0.116-0.162) | 0.141 (0.101-0.178) |
| BOS,MA2 comparison, continuous anion gap | Not applicable | 0.004 (-0.039 to 0.046),<br>p = .87, n=654 |

Footnote: parentheses show 95% confidence intervals. Internal continuous-model
intervals used the cross-validated influence-function estimator [16]; all
other intervals are percentile bootstrap (2,000 resamples, seed 42).
Incremental AUROCs were estimated in the same patients used to fit the
combined models. The BOS,MA2 row reports the AUROC difference (CS-MORT-6 minus
BOS,MA2) with a DeLong P value. The integer score is not scored identically in
the two columns: externally it used lactate categories when observed and
anion-gap categories otherwise, internally a missing component took its
development-median category, and rescoring internally under the external rule
gives 0.720 (Supplementary Table S9). AUROC, area under the receiver operating
characteristic curve; CITL, calibration-in-the-large (negative values indicate
overprediction); EHR, electronic health record. See Supplementary Figures S1
to S4.

## Figure 1. In-hospital mortality by CS-MORT-6 tertile within EHR-derived SCAI stages

Bars show subsequent in-hospital mortality among patients alive and still in
the ICU 24 hours after ICU admission in MIMIC-IV (A) and eICU (B). Tertiles
were defined within each SCAI stage and separately within each cohort. Error
bars show Wilson 95% confidence intervals. Group sizes are reported in
Supplementary Table S12. Stage A was omitted (eight MIMIC-IV patients, no eICU
patients, and no deaths). Supplementary Figures S5 to S7 show sensitivity
analyses, 48-hour score trajectories, and subgroup performance.

---

## Declarations note for the Word build

The Data Availability statement no longer describes the analysis plan as
prespecified. All other declarations, including the Declaration of AI-assisted
technologies, are unchanged from submission.

## Reference list (20; changes from submission at end)

1. Samsky MD, et al. JAMA. 2021;326(18):1840-1850.
2. Baran DA, et al. Catheter Cardiovasc Interv. 2019;94(1):29-37.
3. Jentzer JC, et al. J Am Coll Cardiol. 2019;74(17):2117-2128.
4. Naidu SS, et al. J Am Coll Cardiol. 2022;79(9):933-946.
5. Harjola VP, et al. Eur J Heart Fail. 2015;17(5):501-509.
6. Pöss J, et al. J Am Coll Cardiol. 2017;69(15):1913-1920.
7. Yamga E, et al. J Am Heart Assoc. 2023;12(13):e029232.
8. Ton VK, et al. J Am Coll Cardiol. 2024;84(11):978-990.
9. Zweck E, et al. JACC Heart Fail. 2025;13(10):102611.
10. Johnson AEW, et al. Sci Data. 2023;10:1.
11. Pollard TJ, et al. Sci Data. 2018;5:180178.
12. Collins GS, et al. BMJ. 2024;385:e078378.
13. van Houwelingen HC. Scand J Stat. 2007;34(1):70-85. [ADDED: landmarking]
14. Riley RD, et al. Stat Med. 2019;38(7):1276-1296.
15. Sullivan LM, Massaro JM, D'Agostino RB Sr. Stat Med. 2004;23(10):1631-1660.
16. LeDell E, Petersen M, van der Laan M. Electron J Stat. 2015;9(1):1583-1607. [ADDED: cvAUC]
17. DeLong ER, DeLong DM, Clarke-Pearson DL. Biometrics. 1988;44(3):837-845.
18. Horsfall LJ, et al. Clin Epidemiol. 2025;17:647-662. [ADDED: race correction]
19. Pfohl SR, Foryciarz A, Shah NH. J Biomed Inform. 2021;113:103621. [ADDED: fairness]
20. Paulus JK, Kent DM. NPJ Digit Med. 2020;3:99. [ADDED: fairness framework]

Removed from the submitted list (with the sentences that cited them):
Christodoulou 2019 (model-class comparison sentence, now supplement-only);
Fuernau 2020 (serial-lactate discussion sentence, removed); Moller/DanGer
2024 (microaxial discussion sentence, removed). Numbering is serial by first
appearance. All five added references were read in full before citation.

## Supplement map (build order)

S1 TRIPOD+AI checklist. S2 definitions, cohorts, staging rules and
missing-component handling. S3 model development and card-stability
sensitivity. S4 full model specification, both formulations, exact intercepts,
card, score-to-risk mapping, worked example. S5 baseline characteristics. S6
death-timing distribution. S7 availability and scorability. S8 sensitivity
cohorts, imputation, correlations and VIF. S9 landmark risk bands and
threshold accuracy. S10 external populations and day-1 all-admissions
performance with the BOS,MA2 comparison. S11 redevelopment sensitivity
analyses. S12 within-stage cells, within-stage AUROCs, incremental value and
variants. S13 subgroup discrimination and calibration. S14 48-hour
reassessment and trajectory. Figures: S1 cohort flow with landmark;
S2 calibration curves; S3 decision curves; S4 integer card, predicted versus
observed; S5 within-stage variants; S6 trajectory; S7 subgroups.
