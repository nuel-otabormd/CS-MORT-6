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
contains('locked_external_results.csv', '0.748', '0.759', '0.738', '1047 / 305',
         '0.713', '0.716', 'deployment rule')
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
assert f1e['n'].sum() == 1047, f1e['n'].sum()
contains('external_incremental.csv', '+0.141', '0.759')
fc = pd.read_csv(OUT + 'figure1_eicu_frozen_cuts.csv')
assert len(fc) == 12 and fc['n'].sum() == 1047, (len(fc), fc['n'].sum())
checked += 1
checked += 2

# 48-hour trajectory groups
tr = pd.read_csv(OUT + 'trajectory_symmetric.csv')
ns = set(tr[tr.columns[[c.lower() in ('n', 'count') for c in tr.columns]][0]]
         .astype(int)) if any(c.lower() in ('n', 'count') for c in tr.columns) \
    else set()
if ns:
    assert {785, 978, 496} <= ns, ns
    checked += 1

# Stage-coding and refitting robustness (Supplementary Table S12, panel B)
_r = pd.read_csv(OUT + 'stage_coding_robustness.csv').set_index('tag')
assert round(_r.loc['eICU continuous AG (frozen)', 'd_cat'], 3) == 0.125
checked += 1
assert round(_r.loc['eICU continuous AG (frozen)', 'a_stage_cat'], 3) == 0.630
checked += 1
assert round(_r.loc['eICU integer card (deployment rule)', 'd_cat'], 3) == 0.135
checked += 1
assert round(_r.loc['MIMIC continuous AG (OOF), stage A merged into B', 'd_cat'], 3) == 0.140
checked += 1

# Figure S2 calibration data (external deciles + annotation values)
_ca = pd.read_csv(OUT + 'calibration_annotations.csv').set_index('panel')
assert round(_ca.loc['external_aniongap', 'slope'], 2) == 1.17
checked += 1
assert round(_ca.loc['external_aniongap', 'brier'], 3) == 0.172
checked += 1
assert len(pd.read_csv(OUT + 'external_calibration_curve_ag.csv')) == 10
checked += 1

# Threshold operating characteristics derive from the deployed card (Table S9, panel B)
contains('landmark_thresholds.csv', '0.89', '0.36', '3.32')
# --- card re-derivation: every metric verified, by name ---------------------
# The output-to-expected check is metric-specific: each value is read from its
# own labelled row. The output-to-document check is anchored, so a value must
# appear in its labelled position inside the supplement's point-schedule
# paragraph, not merely somewhere in the file.
_CARD_FMT = {
    'transported_card_oof_auroc':  ('0.7267', 4),
    'rederived_card_oof_auroc':    ('0.7190', 4),
    'transported_minus_rederived': ('0.0076', 4),
    'diff_ci_lower_2p5':           ('0.0034', 4),
    'diff_ci_upper_97p5':          ('0.0121', 4),
    'diff_ci_includes_zero':       ('False',  None),
    'bootstrap_resamples_diff':    ('2000',   None),
    'bootstrap_resamples_points':  ('500',    None),
    'points_lactate_1pt_pct':      ('64.2',   1),
    'points_lactate_2pt_pct':      ('35.8',   1),
    'points_uo_1pt_pct':           ('100.0',  1),
    'points_ohca_arrest_2pt_pct':  ('38.8',   1),
    'points_ohca_arrest_3pt_pct':  ('61.0',   1),
    'points_ohca_arrest_4pt_pct':  ('0.2',    1),
    'points_age_1pt_pct':          ('100.0',  1),
    'points_bun_1pt_pct':          ('100.0',  1),
    'points_rdw_1pt_pct':          ('100.0',  1),
}
# only these five are printed in the supplement; each must sit beside its label
_CARD_DOC = {
    'transported_card_oof_auroc':  'AUROC of {v},',
    'rederived_card_oof_auroc':    'with {v} when',
    'transported_minus_rederived': 'difference {v},',
    'diff_ci_lower_2p5':           '95% CI {v}-',
    'diff_ci_upper_97p5':          '-{v})',
}

_m = pd.read_csv(OUT + 'card_rederivation.csv').set_index('metric')['value'].astype(str).to_dict()
assert set(_m) == set(_CARD_FMT), (
    f"card_rederivation.csv metric set changed: "
    f"missing {set(_CARD_FMT) - set(_m)}, unexpected {set(_m) - set(_CARD_FMT)}")
for _k, (_shown, _dp) in _CARD_FMT.items():
    _got = f"{float(_m[_k]):.{_dp}f}" if _dp is not None else _m[_k]
    assert _got == _shown, f"card_rederivation.csv:{_k} is {_got}, expected {_shown}"
    checked += 1
# internal consistency of the interval and the difference
_lo, _hi = float(_m['diff_ci_lower_2p5']), float(_m['diff_ci_upper_97p5'])
assert (_m['diff_ci_includes_zero'] == 'True') == (_lo <= 0 <= _hi), \
    'card_rederivation.csv: includes-zero flag disagrees with the interval'
assert abs((float(_m['transported_card_oof_auroc']) - float(_m['rederived_card_oof_auroc']))
           - float(_m['transported_minus_rederived'])) < 2e-6, \
    'card_rederivation.csv: difference does not equal the two AUROCs'  # 6-dp rounding
checked += 2
# anchored document check, scoped to the point-schedule paragraph
_sup = open(os.path.join(_B, '..', 'manuscript', 'SUPPLEMENT.md')).read()
assert '(C) Point-schedule sensitivity.' in _sup, \
    'SUPPLEMENT.md: the point-schedule sensitivity paragraph is missing'
_blk = ' '.join(_sup.split('(C) Point-schedule sensitivity.', 1)[1]
                    .split('\n\n', 1)[0].split())
for _k, _tpl in _CARD_DOC.items():
    _need = _tpl.format(v=_CARD_FMT[_k][0])
    assert _need in _blk, f"SUPPLEMENT.md point-schedule paragraph: expected {_need!r}"
    checked += 1

print(f"verify_ledger: {checked} canonical checks passed")
