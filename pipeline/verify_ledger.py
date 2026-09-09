"""Verification gate.

Asserts that the pipeline outputs contain the canonical results reported in the
manuscript, supplement, and response letter. Run after the pipeline completes;
any assertion failure means the outputs no longer match the published numbers.
"""
import os
import pandas as pd

_B = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('CSMORT6_OUT', os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'

checked = 0


def contains(fname, *needles):
    global checked
    text = open(OUT + fname).read()
    for n in needles:
        assert n in text, f"{fname}: expected {n!r}"
        checked += 1


# Internal landmark performance and confidence-interval methods
contains('internal_final_results.csv',
         '0.7339 (0.7140-0.7538)', '0.7337 (0.7143-0.7527)')
# External validation (frozen run): anion gap, lactate, integer card
contains('locked_external_results.csv', '0.715', '0.726', '0.699')
# Redevelopment, deployable pool: paired difference
contains('challenger_result.csv', '-0.014')
# Event timing (exact timestamps): late-death counts and total
contains('event_time_exact.csv', '377', '402', '1188')
# Risk bands, out-of-fold: lowest and highest band mortality
contains('v2_risk_bands_oof.csv', '12.7', '62.2')
# Severity frame (all admissions), both cohorts
contains('severity_frame_final.csv', '0.7582', '0.7320')
# Full model specification: exact intercepts, both formulations
contains('v2_spec_continuous.csv', '-0.806673', '-0.82333')
# Fairness subgroups: every recorded category, race rows total the landmark n
fair = pd.read_csv(OUT + 'fairness_subgroups_lm24.csv')
assert len(fair) == 7, len(fair)
race = fair[~fair.subgroup.isin(['M', 'F', 'Male', 'Female'])]
assert race['n'].sum() == 2694, race['n'].sum()
checked += 2

# Integer card: deployed points (lactate 0/2/4), maximum score 15
card = pd.read_csv(OUT + 'v2_integer_card.csv')
pts = dict(zip(card.variable, card.points_per_level))
assert pts['lactate'] == 2 and pts['aniongap_substitution'] == 2, pts
mx = (2 * pts['lactate'] + 2 * pts['uo'] + pts['ohca_arrest']
      + 2 * pts['age'] + 2 * pts['bun'] + 2 * pts['rdw'])
assert mx == 15, mx
checked += 2

# Within-stage variant cells with sizes and intervals
var = pd.read_csv(OUT + 'figure1_variants_mimic.csv')
assert len(var) == 24 and var['n'].sum() == 2686 * 2, (len(var), var['n'].sum())
checked += 1

# Figure 1 cells: displayed stages sum to the landmark populations minus stage A
f1m = pd.read_csv(OUT + 'figure1_mimic_lm24.csv')
assert f1m['n'].sum() == 2686, f1m['n'].sum()
f1e = pd.read_csv(OUT + 'figure1_eicu_lm24.csv')
assert f1e['n'].sum() == 1586, f1e['n'].sum()
checked += 2

# 48-hour trajectory groups
tr = pd.read_csv(OUT + 'trajectory_symmetric.csv')
ns = set(tr[tr.columns[[c.lower() in ('n', 'count') for c in tr.columns]][0]]
         .astype(int)) if any(c.lower() in ('n', 'count') for c in tr.columns) \
    else set()
if ns:
    assert {785, 978, 496} <= ns, ns
    checked += 1

print(f"verify_ledger: {checked} canonical checks passed")
