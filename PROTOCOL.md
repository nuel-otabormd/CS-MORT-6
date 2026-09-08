# CS-MORT-6 IJC revision: frozen development protocol

Frozen 7 September 2026, before the challenger analysis was run. Approved by
Dr. Otabor in conversation the same day (7 September 2026). No element below may change after the
challenger results are seen. External (eICU) data play no role in any decision
in this document and are used once, at the end, in a single locked execution.

## Frozen primary model: CS-MORT-6-LM24 v2.0

Estimand: in-hospital death after the 24-hour landmark, among patients alive and
in the ICU at exactly 24 hours after ICU admission (n = 2,694; 892 deaths).
Predictors: the six prespecified variables of the submitted CS-MORT-6 (lactate,
urine output rate, out-of-hospital cardiac arrest, age, blood urea nitrogen, red
cell distribution width), most recent value up to 24 h. Continuous model:
winsorize 1st-99th, median-impute, standardize, ridge logistic regression
(L2, C = 0.5), coefficients and intercept refit at the landmark; full exact
specification in outputs/v2_spec_continuous.csv. Anion-gap formulation
identical with harmonized anion gap in place of lactate.

Integer card: the transported v1.1 structure (lactate 0/2/4; urine output
0/1/2 protective; OHCA 0/3; age 0/1/2; BUN 0/1/2; RDW 0/1/2; range 0-15),
retained on prespecified preservation preference after the landmark
re-derivation proved unstable (lactate 1 vs 2 points in 64/36 of bootstraps)
and noninferior, not superior, in discrimination (paired difference +0.0055,
95% CI -0.000 to +0.011 favoring the transported card). Binning is
left-inclusive (pandas.cut right=False) so the written card and the code are
the same instrument. Missing components take the category of the development
median value. Score-to-risk mapping re-estimated at the landmark
(outputs/v2_score_risk_mapping.csv); risk bands 0-3 / 4-5 / 6-7 / 8-15.

## Challenger analysis (decision rule, frozen before running)

Candidate pool (harmonized definitions in the study's frozen extraction
pipeline AND >= 80% observed availability in both databases at 24 h; screen
results in the conversation record of 8 Sep 2026):

  age, OHCA, harmonized anion gap, sodium, chloride, bicarbonate, BUN, RDW,
  creatinine, hemoglobin, minimum systolic BP, mechanical ventilation,
  vasopressor count   (13 candidates)

Excluded by the screen, with observed eICU availability: SpO2 min (78.2%),
GCS (71.7%), lactate (49.1%), urine output (56.7%), bilirubin (59.9%);
platelets and WBC have no harmonized eICU extraction in the frozen pipeline.
The incumbent's lactate and urine output are grandfathered as prespecified
variables of the submitted score; their exclusion binds only the challenger.
Anion gap is a linear combination of sodium, chloride, and bicarbonate;
co-selection is left to the selection procedure and is interpretable if it
occurs. Mechanical ventilation, vasopressor count, and minimum SBP are
support-dependent; if selected, this tradeoff is discussed but is not itself
disqualifying.

Design: 5-fold stratified outer cross-validation repeated 10 times (repeat
seeds 100-109), identical folds for challenger and comparators. Within each
outer training set only: winsorization (1st-99th), median imputation,
standardization; selection by 100 bootstrap resamples of L1 logistic
regression (C = 0.5, saga), selecting predictors with nonzero-coefficient
frequency >= 60%, capped at the top 6 by frequency; final within-fold model =
ridge (C = 0.5) on the selected set; predict the outer test fold. Comparators
on identical folds: v2.0 lactate formulation (primary) and anion-gap
formulation (secondary), fixed six predictors, same preprocessing.

Decision inputs, computed on per-patient out-of-fold probabilities averaged
across the 10 repeats: paired patient-level bootstrap (2,000 resamples) of the
AUROC difference; calibration slope, CITL, Brier with bootstrap CIs; net
benefit at threshold probabilities 20% and 40%.

The six-predictor CS-MORT-6-LM24 v2.0 remains primary unless ALL hold:
1. paired mean AUROC improvement over the v2.0 lactate formulation >= 0.010;
2. the 95% paired bootstrap CI of that difference excludes zero;
3. no material calibration or Brier deterioration, judged on the compared
   intervals, not a fixed slope window;
4. net benefit at 20% and 40% not worse;
5. stable selection: every predictor of the full-data challenger model
   selected in >= 70% of the 50 outer-fold selections;
6. at most six predictors, all from the frozen pool.
A suggestive but uncertain improvement is reported as supplementary and does
not replace the model. The challenger is reported in the supplement regardless
of outcome. MIMIC only; eICU is not consulted.

## External validation (after the identity decision)

One locked execution produces every external number in the revision: v2.0
(both formulations, continuous and integer) at the exact eICU 24-hour landmark
and the all-comers day-1 severity frame; 48-hour landmark analyses; BOS,MA2
comparisons in both frames including the imputed-BOS,MA2 sensitivity. No
model, card, band, threshold, or mapping change afterward. The manuscript
acknowledges that eICU informed the submitted validation and revision
diagnostics, so confirmation in an untouched cohort remains necessary.
