# Protocol amendment: corrected external analysis population

Date: 9 September 2026. Specified before the amended external run was
executed; archived alongside FROZEN_PROTOCOL_20260907.md and hashed in the
ledger manifest.

## Defect being corrected

Internal audit (not a journal reviewer) identified two properties of the
external landmark population that the frozen protocol had not addressed:

1. Unit of analysis. The 1,586 landmark ICU stays represent 1,439 unique
   patients (147 repeat stays, 9.3%); all external estimates treated stays
   as independent. The comparator score's development study excluded
   readmissions.
2. Eligibility timing. Cohort membership used cardiogenic-shock
   documentation from any time in the ICU stay; 431 of 1,586 landmark
   stays (27.2%) had shock first documented after the 24-hour landmark,
   which is inconsistent with evaluating the score at a moment of use.

## Amended definition (fixed before execution)

The primary external landmark population comprises ICU stays that
(a) meet the exact 24-hour landmark (alive and in the ICU at 24 hours),
(b) have cardiogenic shock documented at or before 1,440 minutes from unit
admission, and (c) are the patient's first qualifying stay, selected
deterministically by lowest unitvisitnumber, then lowest
patienthealthsystemstayid, then lowest patientunitstayid.
Pre-run size check from the audit: n=1,047, 305 deaths.

All frozen objects are unchanged: the MIMIC-fitted coefficients,
intercepts, winsorization bounds, imputation medians, scaling constants,
integer card, band boundaries, and score-to-risk mapping are exactly those
of the frozen protocol. Only the external evaluation population changes.

## Sensitivity analyses retained

The previous all-stays landmark population (n=1,586) and the
one-stay-per-patient population without the documentation-timing
restriction (n=1,439) are reported as labeled sensitivity analyses.
The day-1 all-admissions frame (n=1,866) is retained unchanged as the
submitted-design continuity analysis. A further sensitivity zeroes the 18
arrest flags whose first arrest diagnosis was entered after 24 hours.

## New external estimands added under this amendment

Formal external incremental value (stage-only, score-only, stage plus
score AUROC with patient-clustered bootstrap differences and
likelihood-ratio test) and within-stage cells using MIMIC-frozen tertile
cutpoints, mirroring the internal analyses.

No result computed under this amendment may feed back into any model,
card, band, threshold, or mapping.

## Clarification (9 September 2026, recorded before the corresponding rerun)

1. Late-documented arrest flags (first arrest diagnosis after 1,440 minutes;
   5 records in the primary population) are set to zero in the PRIMARY
   external analyses, for the score inputs and for stage assignment alike;
   the unzeroed analysis becomes the sensitivity.
2. The primary external integer-card evaluation follows the printed
   deployment rule exactly: lactate bands when lactate is observed,
   anion-gap bands otherwise. The anion-gap-bands-for-all evaluation is
   retained as the harmonized sensitivity. No point value, band boundary,
   or mapping changes.
3. Incremental value over the EHR-derived stage is reported with matched
   score formulations in both cohorts (continuous anion-gap model, and the
   integer card), with stage variants that remove the arrest rule reported
   as robustness analyses.
4. "First qualifying stay" denotes the deterministic selection order
   (unitvisitnumber, then patienthealthsystemstayid, then
   patientunitstayid); chronological order across separate hospitalizations
   is not always establishable in eICU.
