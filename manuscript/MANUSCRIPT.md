# CS-MORT-6 manuscript source

The authored text of the manuscript. Every value in it is produced by the
pipeline in `../pipeline` and written to `../outputs`; `verify_sources.py`
asserts that mechanically. Word-count convention: the 1,500-word limit
covers the prose of sections 1-5 only, excluding title page, highlights,
abstract, keywords, Table 1, figure legend, declarations, and references.

---

## Title

CS-MORT-6: A Mortality Risk Score That Adds Resolution Within EHR-Derived SCAI Stages in Cardiogenic Shock

## Highlights

A six-variable integer score refines mortality risk within EHR-derived SCAI stages.
Externally validated at a 24-hour landmark in 1,047 patients across 117 hospitals.
Within a SCAI stage, risk tertiles differed by 20 to 47 percentage points.
Discrimination was comparable with BOS,MA2 using six routinely collected variables.
48-hour reapplication and real-time availability need prospective evaluation.

## Abstract

Background: Cardiogenic shock carries an in-hospital mortality of 30 to 50%, and the ordinal SCAI shock classification leaves risk unquantified within a stage. Scores built from first-24-hour measurements may retain patients who die within that window.

Methods: From MIMIC-IV we identified 3,103 adults with documented cardiogenic
shock. The primary evaluation was among patients alive and in the ICU at the
24-hour landmark (n=2,694; 892 deaths). CS-MORT-6 uses six predictors (lactate or anion gap, urine output,
cardiac arrest at presentation, age, blood urea nitrogen, red cell
distribution width) as a 0-to-15 integer card; continuous coefficients,
intercepts, and the card's risk mapping were estimated at the landmark, retaining
the point schedule. The
frozen model was applied to the eICU landmark (n=1,047, 117 hospitals;
first stay per patient, shock documented by 24 hours).

Results: The score added discrimination beyond the EHR-derived SCAI stage
in both databases (+0.139, 95% CI +0.116 to +0.163 in MIMIC-IV;
+0.141, +0.101 to +0.178 in eICU), and within-stage tertiles separated by
20 to 47 percentage points. Internal cross-validated area under the curve (AUROC) was 0.734 (95%
CI 0.714 to 0.754); external anion-gap AUROC was 0.748 (0.715 to 0.780;
calibration-in-the-large 0.00); the integer card reached 0.759. Risk
bands were monotonic (12.7% to 62.2% internally; 8.8% to 59.3%
externally). Discrimination was comparable with BOS,MA2 (difference
+0.004, 95% CI -0.039 to +0.046).

Conclusions: When computed at 24 hours, CS-MORT-6 quantified residual
risk within EHR-derived SCAI stages and preserved anion-gap external
calibration. Reapplication at 48 hours and real-time
availability require prospective evaluation.

Keywords: cardiogenic shock; risk score; SCAI stage; landmark analysis; external validation; mortality

---

## 1. Introduction

Cardiogenic shock remains among the most lethal conditions in cardiovascular
medicine, with in-hospital mortality of 30 to 50% despite advances in
revascularization, mechanical circulatory support (MCS), and systems of care
[1]. The
Society for Cardiovascular Angiography and Interventions (SCAI) shock
classification communicates severity and tracks mortality across its five
stages [2,3], but the stage is a qualitative category, and patients within
the same stage show substantial residual heterogeneity in outcome [4].
Existing quantitative scores each carry a practical constraint: CardShock
requires echocardiographic ejection fraction [5], IABP-SHOCK II requires
post-procedural coronary flow [6], and the BOS,MA2 score avoids imaging but
relies on support-dependent vital signs [7]; all are computed once. Serial SCAI re-staging and machine-learning phenotypes refine risk further but need registry infrastructure [8,9]. Scores built from measurements accumulated over the first
24 hours may retain patients who die within that window [7], mixing
severity characterization with prediction. We developed and externally validated CS-MORT-6, an integer score that quantifies residual mortality risk within electronic health record (EHR)-derived SCAI stages, evaluated among patients alive at a 24-hour landmark [10].

## 2. Methods

We used MIMIC-IV (Beth Israel Deaconess Medical Center, 2008-2022) for
development and the eICU Collaborative Research Database (208 hospitals,
2014-2015) for external validation [11,12]; reporting followed TRIPOD+AI [13] (completed checklist, Supplementary Table S1). Adults aged 18 years or
older with cardiogenic shock were identified in MIMIC-IV by a
documentation-anchored phenotype (diagnostic code or affirmed
discharge-summary documentation) plus at least one objective hypoperfusion
criterion within 24 hours (criteria, Supplementary Table S2); case
identification is retrospective, using full-hospitalization documentation. The eICU
cohort was identified from cardiogenic-shock diagnosis entries;
the primary external population is each patient's first landmark stay
with shock documented by 24 hours (definitions and sensitivity
populations, Supplementary Table S2). Landmark eligibility required being alive and in the ICU at 24 hours (ICU
discharge at or after, and no recorded death at or before, that time). The outcome was in-hospital death after the landmark; the landmark population's 892 deaths meet the minimum for re-estimating six fixed predictors, while the earlier selection pool had not met its own minimum (Supplementary Table S2) [14].

CS-MORT-6 comprises six predictors fixed through staged development, a
58-parameter stability screen (each selected in 100% of bootstraps) plus
clinically guided reduction (Supplementary Table S4):
lactate, blood urea nitrogen, and red cell distribution width as the most
recent values up to 24 hours; urine output as the cumulative first-24-hour
rate; and age and cardiac arrest at presentation (a diagnosis-based proxy,
Supplementary Table S2) as admission characteristics. A separately fitted formulation substitutes the harmonized
anion gap (sodium minus chloride minus bicarbonate) for lactate,
motivated by lactate availability at the landmark (80.8% development, 52.5%
external). Continuous models were ridge logistic regression (C=0.5, untuned); collinearity was low (Supplementary Table S12).
Continuous-model coefficients, intercepts, and the card's score-to-risk
mapping were estimated in the landmark population; the complete
specification, including exact intercepts, is in Supplementary Table S3.
The 0-to-15 point schedule was derived in the full development cohort, with
points proportional to the coefficients of a logistic model on the
categorized predictors in the spirit of the Sullivan points system [15],
and retained after a landmark re-derivation sensitivity analysis
(Supplementary Table S4); thresholds are left-inclusive, and a missing component scores its development-median category (Supplementary Table S3). Discrimination was summarized by the area under the receiver operating characteristic curve (AUROC). Internal validation used five-fold cross-validation with preprocessing inside folds; the primary interval used the cross-validated
influence-function estimator [16].
Calibration used the calibration slope, calibration-in-the-large (CITL), and the Brier
score. For external validation the entire pipeline was fixed on the development data and applied unchanged to the eICU landmark under prespecified variable harmonization, with head-to-head comparison against BOS,MA2 by the DeLong method [7,17] and exploratory 48-hour reapplication. The five-stage SCAI classification was operationalized from hypotension, lactate, vasoactive and device support, and cardiac arrest, adapting consensus definitions [2-4] (rules, Supplementary Table S9); incremental value used likelihood-ratio testing and paired bootstrap.
Analyses used Python 3.9 and R with a fixed random seed; scripts and outputs accompany this article.

## 3. Results

The development cohort comprised 3,103 adults with documented cardiogenic shock; in-hospital mortality was 38.3% (baseline characteristics in Supplementary Table S5); 249 deaths occurred within 24 hours and 779 (65.6%) after 48 hours
(Supplementary Table S7). In the
landmark population (n=2,694; mortality 33.1%), cross-validated AUROC was 0.734 (95% CI 0.714 to 0.754) for the lactate formulation, 0.726
(0.707 to 0.746) for the anion-gap formulation, and 0.727 for the
integer card (Table 1). In
the eICU landmark (n=1,047, 117 hospitals, 29.1% mortality), the frozen
anion-gap model reached 0.748 (0.715 to 0.780; CITL 0.00), the lactate
formulation 0.759 (0.728 to 0.789; CITL -0.25), and the deployment-rule
integer card 0.759 (0.729 to 0.790); sensitivity populations: 0.713 to 0.716 (Supplementary Table S6). Risk bands (scores 0-3, 4-5, 6-7, 8-15) were monotonic in both cohorts,
from 12.7% to 62.2% internally and 8.8% to 59.3% externally (Supplementary
Table S8). Day-1 all-admissions estimates were higher (internal 0.778, external 0.749; Supplementary Table
S6). On patients scorable for both models, discrimination was comparable with BOS,MA2 in the day-1 analysis
(0.749 versus 0.743; difference +0.006, 95% CI -0.026 to +0.038) and the
landmark analysis (0.755 versus 0.751; difference +0.004, 95% CI
-0.039 to +0.046). CardShock and IABP-SHOCK II were not computable in eICU because ejection fraction and coronary flow are unavailable [5,6].

Within EHR-derived SCAI stages, the score separated low-risk and high-risk tertiles by 20 to 47 percentage points, with similar separation in eICU (Figure 1; cell sizes and confidence intervals in Supplementary Table S9). Adding the score to the EHR-derived stage
increased AUROC by +0.139 (95% CI +0.116 to +0.163) in MIMIC-IV and +0.141
(+0.101 to +0.178) in eICU (both P < .001; matched
formulations, Supplementary Table S9), whereas
adding the stage to the score changed it by at most +0.008; in both cohorts
the gradient persisted without cardiac arrest, with a non-staging
four-variable sub-score, and with the arrest rule removed from staging,
and the increment persisted with the stage recoded as unordered
categories (eICU +0.125, +0.090 to +0.160; Supplementary Table S9). At the exploratory 48-hour landmark, recomputation outperformed the 24-hour prediction internally (0.739 versus
0.714; paired difference +0.024, 95% CI +0.012 to +0.036), while externally
the confidence interval spanned zero (0.725 versus 0.716;
+0.009, 95% CI -0.012 to +0.030); among patients with intermediate
24-hour scores, mortality was 24.0% with improvement and 43.3% with
worsening (adjusted odds ratio 1.37 per point, 95% CI 1.27 to 1.47; Supplementary Table S10). External observed availability was 96.4% for anion gap, 60.6% for urine
output, and 52.5% for lactate; all anion-gap-model inputs were observed in
53.3% (Supplementary Table S11). AUROC spanned 0.70 to 0.81 across sex and race subgroups; CITL spanned
-0.37 (Asian, n=67) and -0.30 (Black, n=267) to +0.36 in Other/Unknown
patients (Supplementary Table S13).

## 4. Discussion

CS-MORT-6 is a six-variable integer score for in-hospital mortality in cardiogenic shock that adds quantitative resolution within a recorded-data operationalization of the SCAI stage: in MIMIC-IV the stage alone discriminated at
0.589, adding the score raised AUROC by +0.139 while adding the stage to
the score changed it by +0.001, and within-stage gradients were monotonic in both databases. Landmark discrimination is moderate (0.73 to 0.76) and comparable with BOS,MA2; the
further contributions are computability from routine variables and
preserved anion-gap external calibration. Fully nested redevelopment did not improve on the six-variable model; lactate and
urine output, weakly reselected at the landmark, were retained by their
selection during development (Supplementary Table S14). Positioned as a stratification aid rather than a treatment determinant, the score may prompt earlier evaluation for MCS, transfer, or a goals-of-care discussion.

Subgroup calibration differences are reported transparently rather than
corrected: recorded race is a social classification that can proxy
measurement, case mix, and site effects; race-based correction risks
entrenching disparity [18]. We did not apply fairness-weighted
training, absent a defined allocation decision or fairness criterion and
given empirical evaluations show heterogeneous and
often adverse within-group effects [19,20]; we recommend site-level recalibration and equity monitoring before
deployment [18].

### 4.1. Study limitations

Ascertainment relied in part on documented recognition of cardiogenic shock, so the score applies to recognized shock and cannot be assumed to perform on early or unrecognized presentations. Development was single-center, though external validation spanned 117 hospitals. The 48-hour analysis reapplies
the 24-hour model rather than fitting a separate 48-hour model; its
external discrimination near 0.72 does not yet support serial use.
Real-time availability is not established: complete observed inputs were
present in only 53.3% of external landmark patients, so scores often rest
on the stated imputation rule, and early emergency-department use
is untested. The external stage is a coarse operationalization, the external cohort
definition is broader, and eICU informed both
the comparator's development and our analytic choices; confirmation in
an untouched cohort is needed.

## 5. Conclusions

In two large intensive care databases, CS-MORT-6, evaluated at a 24-hour landmark, refined mortality risk within EHR-derived SCAI stages, preserved anion-gap calibration on external validation, and retained moderate discrimination. Its main contribution is not superior discrimination but quantification of the risk that qualitative staging leaves unresolved; serial use and real-time bedside performance
require prospective evaluation.

---

## Table 1 (main text): performance at the 24-hour landmark

| Metric | MIMIC-IV (development) | eICU (external, primary) |
|---|---|---|
| n / deaths / mortality | 2,694 / 892 / 33.1% | 1,047 / 305 / 29.1% |
| Continuous, lactate | 0.734 (0.714-0.754) | 0.759 (0.728-0.789) |
| Continuous, anion gap | 0.726 (0.707-0.746) | 0.748 (0.715-0.780) |
| Integer card (0-15) | 0.727 (0.706-0.747) | 0.759 (0.729-0.790) |
| Calibration slope / CITL (anion-gap formulation) | 0.99 / 0.00 (out-of-fold) | 1.17 / 0.00 |
| Brier (anion-gap formulation) | 0.189 (out-of-fold) | 0.172 |
| Incremental over EHR-derived stage | +0.139 (+0.116 to +0.163) | +0.141 (+0.101 to +0.178) |
| BOS,MA2 comparison | - | +0.004 (-0.039 to +0.046), P = .87, n=654 |

Footnote: internal CI by cross-validated influence function [16]; the external integer card follows the deployment rule (lactate bands when lactate is observed, anion-gap bands otherwise) and the internal card scores missing components by the median-category rule (deployment-rule rescoring, Supplementary Table S8); the external primary is one stay per patient with shock
documented by 24 hours; landmark eligibility, sensitivity populations, and
the day-1 (all admissions) analyses in Supplementary Tables S2 and S6; BOS,MA2 difference CIs are patient-level bootstrap, with P values by the DeLong method; cohort flow in Supplementary Figure S1, calibration curves in Supplementary Figure S2, decision curves in Supplementary Figure S3 and Table S15, a nomogram of the continuous anion-gap model in Supplementary Figure S7, and the card's predicted and observed risk by score in Supplementary Figure S8.

## Figure 1

Within-stage risk resolution by EHR-derived SCAI stage. In-hospital
mortality by CS-MORT-6 score tertile (low, mid, high) within each
EHR-derived SCAI stage (B-E) in the MIMIC-IV and eICU cohorts at the
24-hour landmark. Whiskers are Wilson 95% confidence intervals; cell sizes are in Supplementary Table S9; stage A (n=8 in MIMIC-IV,
none in eICU, no deaths) is not displayed. Within-stage variants, the 48-hour score trajectory, and subgroup performance appear in Supplementary Figures S4 to S6. Cells from figure1_mimic_lm24.csv and
figure1_eicu_lm24.csv.

---

## Declarations note for the Word build

The Declaration of AI-assisted technologies is updated to read: "During the
preparation of this work the authors used Claude Code (Anthropic) to support
the development and review of analytical code and database queries. The
authors reviewed, tested, and verified all code and take full responsibility
for the content of the published article." The Data Availability statement
no longer describes the analysis plan as prespecified. Other declarations
are unchanged from submission.

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
10. van Houwelingen HC. Scand J Stat. 2007;34(1):70-85. [ADDED: landmarking]
11. Johnson AEW, et al. Sci Data. 2023;10:1.
12. Pollard TJ, et al. Sci Data. 2018;5:180178.
13. Collins GS, et al. BMJ. 2024;385:e078378.
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

S1 TRIPOD+AI checklist (updated). S2 definitions, landmark eligibility rule,
missing-component rule, sample-size statement. S3 full model specification,
both formulations and frames, exact intercepts, card, score-to-risk mapping,
worked example. S4 development history: model-class bake-off (provenance
labeled), card derivation and stability sensitivity. S5 baseline
characteristics. S6 external populations (primary and sensitivity) and day-1 all-admissions performance with BOS,MA2
native comparison and imputation-based exploratory sensitivity. S7
event-time distribution (anomalies footnoted). S8 landmark risk bands and
threshold accuracy. S9 within-stage cells with CIs, within-stage AUROCs,
incremental value, arrest-free and non-staging variants, and the stage
assignment rules for both cohorts. S10 48-hour
reassessment and symmetric trajectory. S11 availability and scorability
(24-hour primary, 48-hour secondary). S12 sensitivity cohorts, chained-equations
imputation, correlations and VIF. S13 fairness subgroups. S14 redevelopment sensitivity
analyses with selection frequencies. S15 decision curves (frozen-vs-frozen
primary, in-sample recalibrated sensitivity). Figures: S1 cohort flow with
landmark; S2 calibration curves; S3 decision curves; S4 within-stage
variants; S5 trajectory; S6 subgroups; S7 nomogram.
