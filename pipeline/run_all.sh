#!/bin/sh
# Runs the complete CS-MORT-6 revision pipeline in dependency order.
# Inputs: extraction CSVs in $CSMORT6_DATA (default ../data), produced by the
# queries in ../sql against the BigQuery study dataset. Outputs: aggregate CSVs
# in $CSMORT6_OUT (default ../outputs). Patient-level intermediates stay in the
# data directory and are never committed.
set -e
cd "$(dirname "$0")"
for s in 01_develop_landmark 02_integer_card 03_redevelopment_deployable \
         04_external_validation 05_internal_analyses 06_external_descriptive \
         07_paired_inference 08_severity_frame 09_supplement_tables; do
  echo "== $s =="
  python3 "$s.py"
done
Rscript 10_sample_size.R
python3 verify_ledger.py
