# CS-MORT-6

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20617606.svg)](https://doi.org/10.5281/zenodo.20617606)

Code and reproduction materials for **"CS-MORT-6: A Mortality Risk Score That Adds
Resolution Within EHR-Derived SCAI Stages in Cardiogenic Shock"** (International
Journal of Cardiology).

CS-MORT-6 is a six-variable integer mortality score for documented cardiogenic shock
(lactate or a harmonized anion-gap substitution, urine output, cardiac arrest at
presentation, age, blood urea nitrogen, red cell distribution width), developed in MIMIC-IV
and externally evaluated in the eICU Collaborative Research Database. The primary
evaluation is a 24-hour landmark analysis: performance is estimated among patients
alive and in the ICU at 24 hours, the point at which the completed score could first
be used. Day-1 all-admissions (severity-frame) estimates are reported alongside for
comparability with existing scores. Reporting follows TRIPOD+AI.

## Protocol and verification

The analysis protocol, including the decision rule for the redevelopment
sensitivity analyses specified and archived before those analyses were run, is in
`PROTOCOL.md` with its original date.

Every number in the manuscript and supplement is produced by this pipeline, and
that is enforced rather than asserted. Two gates run at the end of every
execution: `pipeline/verify_ledger.py` checks the canonical results against the
committed outputs, and `pipeline/verify_sources.py` checks that every numeric
value appearing in `manuscript/MANUSCRIPT.md` and `manuscript/SUPPLEMENT.md`
is derivable from `outputs/` or from the recorded run log. From the extraction
files the pipeline reproduces all 30 output tables byte for byte.

## Structure

- `sql/` — BigQuery extraction queries (cohort, features, SCAI components, eICU).
- `DATA_INPUTS.md` — every input file the pipeline reads: contents, row count,
  and the query or rule that produces it.
- `pipeline/01..09_*.py` — the analysis pipeline in dependency order, from landmark
  development through the supplement's source tables. `pipeline/run_all.sh` runs
  everything and writes `outputs/RUN_LOG.txt`.
- `pipeline/10_sample_size.R` — minimum sample size (Riley criteria, pmsampsize).
- `pipeline/11_stage_coding_robustness.py` — stage-coding and refitting
  robustness for the incremental-value analyses (categorical versus ordinal
  stage, models refit within every bootstrap resample; Supplementary Table S9).
- `pipeline/12_external_calibration.py` — external calibration deciles and
  the calibration annotation values for Figure S2.
- `pipeline/13_render_figures.R` — Figure 1 and Supplementary Figures S1-S8,
  rendered from the outputs tables alone.
- `pipeline/verify_ledger.py` — gate: canonical results match the published values.
- `pipeline/verify_sources.py` — gate: every value in the manuscript and
  supplement sources traces to this pipeline.
- `manuscript/MANUSCRIPT.md`, `manuscript/SUPPLEMENT.md` — the authored text of
  the paper and its supplement, the documents of record for the submitted Word
  files. Step 09 emits regenerated table blocks for cross-checking only.
- `outputs/` — aggregate result tables and `RUN_LOG.txt`, the console record of
  the run (no patient-level data).
- `figures/` — Figure 1 (PNG and 600-dpi TIFF) and Supplementary Figures S1-S8.
- `PROTOCOL.md` — frozen analysis protocol, including the pre-specified decision
  rule for the redevelopment sensitivity analyses.

## Reproduction

1. Obtain credentialed access to MIMIC-IV and eICU-CRD via PhysioNet and run the
   `sql/` queries against BigQuery to produce the extraction CSVs. `DATA_INPUTS.md`
   lists every file the pipeline expects, with its columns and its source query.
2. Place the extraction CSVs in `data/` (gitignored), or point `CSMORT6_DATA` at
   their location. Patient-level files must be stored in accordance with the
   PhysioNet data use agreement and are never committed to this repository.
3. `sh pipeline/run_all.sh` — runs the pipeline end to end with fixed seeds and
   finishes with both verification gates. A clean run reproduces every committed
   output table byte for byte.

Environment: Python 3.9+ with the pinned versions in `requirements.txt`; R with
`pmsampsize` for the sample-size calculation.

## Data availability

MIMIC-IV and eICU-CRD are available to credentialed researchers through PhysioNet.
This repository contains code and aggregate outputs only.

## License

MIT (see `LICENSE`).
