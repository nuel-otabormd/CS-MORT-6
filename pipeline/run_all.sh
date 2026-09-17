#!/bin/sh
# Runs the complete CS-MORT-6 pipeline in dependency order and records the
# console output as outputs/RUN_LOG.txt, so every value printed during the
# run is part of the archive.
#
# Inputs:  extraction CSVs in $CSMORT6_DATA (default ../data), produced by the
#          queries in ../sql against the BigQuery study dataset.
# Outputs: aggregate CSVs in $CSMORT6_OUT (default ../outputs), figures in
#          $CSMORT6_FIG (default ../figures). Patient-level intermediates stay
#          in the data directory and are never committed.
#
# Three gates run at the end and all must pass:
#   verify_ledger.py   the canonical results match the published values
#   verify_sources.py  every value in manuscript/*.md traces to this pipeline
#   verify_tables.py   every regenerated table value is carried into the supplement

cd "$(dirname "$0")"
OUTDIR="${CSMORT6_OUT:-../outputs}"
mkdir -p "$OUTDIR"
LOG="$OUTDIR/RUN_LOG.txt"

{
  set -e
  echo "CS-MORT-6 pipeline run"
  python3 --version 2>&1
  Rscript --version 2>&1 | head -1
  for s in 01_develop_landmark 02_integer_card 03_redevelopment_deployable \
           04_external_validation 05_internal_analyses 06_external_descriptive \
           07_paired_inference 08_severity_frame 09_supplement_tables; do
    echo "== $s =="
    python3 "$s.py"
  done
  echo "== 10_sample_size =="
  Rscript 10_sample_size.R
  echo "== 11_stage_coding_robustness =="
  python3 11_stage_coding_robustness.py
  echo "== 12_external_calibration =="
  python3 12_external_calibration.py
  echo "== 15_hospital_heterogeneity =="
  python3 15_hospital_heterogeneity.py
  echo "== 16_external_risk_bands =="
  python3 16_external_risk_bands.py
  echo "== 13_render_figures =="
  Rscript 13_render_figures.R
  echo "== 14_reported_values =="
  python3 14_reported_values.py
  echo "== verify_ledger =="
  python3 verify_ledger.py
} > "$LOG" 2>&1
status=$?
cat "$LOG"
[ "$status" -eq 0 ] || exit "$status"

# The redirect above is closed and flushed before the gates read the log.
# Deliberately NOT appended to the log: the gate reads the log, so writing
# its output there would let it satisfy itself on the next run.
echo "== verify_sources =="
python3 verify_sources.py
echo "== verify_tables =="
python3 verify_tables.py
