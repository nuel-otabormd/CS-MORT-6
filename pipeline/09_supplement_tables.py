"""Supplement table assembly.

Builds the supplementary tables from pipeline outputs and computes landmark
threshold accuracy.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
DATA    = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'
SCRATCH = DATA
OUT     = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
DOC     = _os.environ.get('CSMORT6_SUPPLEMENT', OUT + 'SUPPLEMENT_TABLES.md')

def md(df, floatfmt=None):
    df = df.copy()
    if floatfmt:
        for c in df.columns:
            if df[c].dtype.kind == 'f':
                df[c] = df[c].map(lambda v: floatfmt % v)
    header = '| ' + ' | '.join(str(c) for c in df.columns) + ' |'
    sep = '|' + '|'.join(['---'] * len(df.columns)) + '|'
    rows = ['| ' + ' | '.join(str(v) for v in r) + ' |' for r in df.values]
    return '\n'.join([header, sep] + rows)

# ---- landmark threshold table (computed inline, saved) ----
# score the landmark population with the deployed card itself (the stored
# score_v2 column is step 01's re-derivation variant, not the deployed card)
import os as _os
_gl = {'__file__': _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '05_internal_analyses.py')}
_src = open(_gl['__file__']).read()
exec(compile(_src.split('# ============ 1+2.')[0], '05_partA', 'exec'), _gl)
y = _gl['y']; s = _gl['card_score'](_gl['lm'], _gl['MED'])
rows = []
for thr in [4, 6, 8, 9]:
    pred = s >= thr
    tp = int(((pred) & (y == 1)).sum()); fp = int(((pred) & (y == 0)).sum())
    fn = int(((~pred) & (y == 1)).sum()); tn = int(((~pred) & (y == 0)).sum())
    sens = tp / (tp + fn); spec = tn / (tn + fp)
    rows.append(dict(threshold=f">= {thr}", sensitivity=f"{sens:.2f}", specificity=f"{spec:.2f}",
                     PPV=f"{tp/(tp+fp):.2f}", NPV=f"{tn/(tn+fn):.2f}",
                     LRpos=f"{sens/(1-spec):.2f}", LRneg=f"{(1-sens)/spec:.2f}"))
thr_tab = pd.DataFrame(rows)
thr_tab.to_csv(OUT + 'landmark_thresholds.csv', index=False)

spec = pd.read_csv(OUT + 'v2_spec_continuous.csv')
card = pd.read_csv(OUT + 'v2_integer_card.csv')
mapping = pd.read_csv(OUT + 'v2_score_risk_mapping.csv')
bands = pd.read_csv(OUT + 'v2_risk_bands_oof.csv')
evt = pd.read_csv(OUT + 'event_time_exact.csv')
traj = pd.read_csv(OUT + 'trajectory_symmetric.csv')
corr = pd.read_csv(OUT + 'correlation_matrix_lm24.csv', index_col=0)
fair = pd.read_csv(OUT + 'fairness_subgroups_lm24.csv')
f1m = pd.read_csv(OUT + 'figure1_mimic_lm24.csv')
f1e = pd.read_csv(OUT + 'figure1_eicu_lm24.csv')
selD = pd.read_csv(OUT + 'challenger_selection.csv')
selS = pd.read_csv(OUT + 'challenger_symmetric_selection.csv')
avail = pd.read_csv(OUT + 'availability_by_horizon_mimic.csv')
dca = pd.read_csv(OUT + 'dca_lm24_common.csv')

D = []

D.append("## Table S4. Full model specification (landmark estimation)\n\n(A) Continuous models, exact values (source: v2_spec_continuous.csv)\n\n"
         + md(spec.fillna('')) +
"""

Predicted probability = 1 / (1 + exp(-(intercept + sum of beta x z))), with
z = (winsorized, median-imputed value - mean) / SD; the raw-scale column
allows direct computation from raw values. Worked example (Word build): a
72-year-old with lactate 3.1 mmol/L, urine output 0.4 mL/kg/h, no OHCA, BUN
41 mg/dL, RDW 15.9%.

(B) Integer card (points per category; range 0-15)

""" + md(card) + """

Anion-gap substitution when lactate is unavailable: < 12 / 12-18 / >= 18
scored 0 / 2 / 4. Thresholds are left-inclusive.

(C) Score-to-risk mapping at the landmark (source: v2_score_risk_mapping.csv)

""" + md(mapping))

# Day-1 (all-admissions) block: built from the locked outputs rather than
# maintained by hand. An earlier hand-typed version of this table carried
# three confidence-interval bounds from a superseded bootstrap run
# (0.733, 0.725, +0.038) and misattributed the internal slope 0.98 to the
# anion-gap formulation; because it fed verify_tables, the gate was
# comparing the supplement against stale literals. Only two cells are
# literals now, both declared in manuscript/CARRIED_FORWARD.md as values
# of the submitted analysis: the internal day-1 lactate AUROC with its CI,
# and the internal out-of-fold slope 0.98 (lactate formulation).
from decimal import Decimal, ROUND_HALF_UP
import re as _re
def _r3(txt):
    """Round every >=4-decimal numeral to 3 decimals, half-up on the digits."""
    return _re.sub(r'\d+\.\d{4,}', lambda m: str(
        Decimal(m.group(0)).quantize(Decimal('0.001'), ROUND_HALF_UP)), txt)
_lock = pd.read_csv(OUT + 'locked_external_results.csv')
_LK = {(r['frame'], r['item']): str(r['value']) for _, r in _lock.iterrows()}
_sev = {r[0]: str(r[1]) for r in pd.read_csv(OUT + 'severity_frame_final.csv').values}
_agcv = {r[0]: str(r[1]) for r in pd.read_csv(OUT + 'allcomers_aniongap_cv.csv').values}
_bos = _LK[('allcomers', 'all-comers (native frame, v1.1 AG): model vs BOS,MA2')]
_bos = _bos.replace(', diff', '; diff').replace(', DeLong P=0.69', '; P = .69')
_slope, _citl = _LK[('allcomers', 'v1.1 anion gap slope/CITL')].split(' / ')
_citl = _citl[0] + str(Decimal(_citl[1:]).quantize(Decimal('0.01'), ROUND_HALF_UP))
D.append("""## Table S10(B). Day-1 performance among all admissions (severity frame)

| Metric | MIMIC-IV (n=3,103) | eICU (1,866 stays; 132 hospitals) |
|---|---|---|
| Continuous, lactate | 0.778 (0.760-0.794) | %s |
| Continuous, anion gap | %s | %s |
| Integer card | %s | %s |
| Calibration | out-of-fold slope 0.98 (lactate formulation) | anion gap slope %s, CITL %s |
| BOS,MA2 head-to-head (n=1,127) | - | %s |""" % (
    _LK[('allcomers', 'v1.1 lactate AUROC')],
    _r3(_agcv['all-comers anion-gap CV AUROC (day-1 frame)']),
    _LK[('allcomers', 'v1.1 anion gap AUROC')],
    _r3(_sev['severity internal integer corrected OOF']),
    _r3(_sev['severity external integer AG corrected']),
    _slope, _citl, _bos))

D.append("## Table S6. Death-timing distribution, exact timestamps (source: event_time_exact.csv)\n\n" + md(evt) +
"""

Two records carry death timestamps preceding ICU admission and one death has
no timestamp; all three are retained in mortality counts and disclosed here.
65.6% of deaths occur after 48 hours.""")

D.append("## Table S9. Landmark risk bands and threshold operating characteristics\n\n(A) Risk bands, out-of-fold (source: v2_risk_bands_oof.csv); eICU external bands in the locked-run results\n\n"
         + md(bands) + """

eICU primary landmark (deployment-rule card), from the locked run: Low 8.8%
(6.1-12.6, n=296), Moderate 18.8% (14.8-23.7, n=292), High 39.6% (33.7-45.8,
n=245), Very high 59.3% (52.7-65.7, n=214).

(B) Diagnostic accuracy at integer thresholds, landmark population (source:
landmark_thresholds.csv)

""" + md(thr_tab))

D.append("## Table S12. Within-stage resolution and incremental value\n\n(A) Within-stage tertile mortality, exact landmark (sources: figure1_mimic_lm24.csv, figure1_eicu_lm24.csv)\n\n"
         + md(pd.concat([f1m, f1e])) + """

(B) Incremental value (MIMIC-IV, landmark): EHR-derived stage alone AUROC
0.589; score alone 0.727; stage plus score 0.728; adding score to stage
+0.139 (95% CI +0.116 to +0.163; likelihood-ratio chi-square 348.2,
P < .001); adding stage to score +0.001. Within-stage AUROC: B 0.636
(0.579-0.692), C 0.689 (0.651-0.724), D 0.756 (0.717-0.793), E 0.728
(0.689-0.765).

(C) Robustness of the gradient: tertile mortality by stage using the
OHCA-free card (MIMIC B 16/30/37, C 16/35/46, D 13/27/58, E 30/49/73) and a
four-variable sub-score of variables taking no part in staging (B 16/32/36,
C 15/32/46, D 12/34/53, E 35/51/68).""")

D.append("## Table S14. 48-hour reassessment and score trajectory\n\n" + """
(B) Symmetric trajectory (source: trajectory_symmetric.csv)

""" + md(traj) + """

Adjusted odds ratio per one-point 24-to-48-hour increase, adjusted for the
24-hour score: 1.37 (95% CI 1.27-1.47), P < .001; generator archived in the
pipeline.""")

D.append("## Table S7. Observed-data availability and scorability\n\n" + """
(A) Exact 24-hour landmark. MIMIC-IV: lactate 80.8%, anion gap 99.6%, urine
output 94.2%, BUN 99.7%, RDW 99.1%; all anion-gap-model inputs 93.2%; all
lactate-model inputs 75.6% (source: reported_values.csv). eICU primary
population: lactate 52.5%, anion gap 96.4%, urine output 60.6%, BUN 97.4%,
RDW 89.5%; all anion-gap-model inputs 53.3%; all lactate-model inputs 29.5%
(source: locked_external_results.csv, LM24 rows).

(B) eICU 48-hour landmark, primary population (cumulative): anion gap 98.6%,
BUN 99.4%, RDW 93.8%, urine output 64.8%, lactate 56.9%; all
anion-gap-model inputs 60.7% (source: locked_external_results.csv, LM48
rows).

(C) Availability by horizon, MIMIC in-ICU populations (temporal trend;
source: availability_by_horizon_mimic.csv)

""" + md(avail))

D.append("## Table S8. Sensitivity analyses, imputation, and collinearity\n\n" + """
(A) Sensitivity cohorts (landmark, frozen model out-of-fold): ICD-confirmed
only 0.734 (n=2,452), Sepsis-3 excluded 0.747 (n=1,321), non-OHCA subgroup
0.724 (n=2,438), OHCA-free integer card 0.711.

(B) Imputation: median 0.734 (slope 0.99) versus stochastic
chained-equations imputation 0.725 (slope 1.01).

(C) Variance inflation factors (landmark): lactate model, all at or below
1.16; anion-gap model, all at or below 1.31 (largest: BUN). Pearson
correlations (source: correlation_matrix_lm24.csv):

""" + md(corr.reset_index()))

D.append("## Table S13. Subgroup discrimination and calibration (landmark; source: fairness_subgroups_lm24.csv)\n\n" + md(fair) + """

Recorded race is a social classification; differences may reflect
measurement frequency, case mix, admission pathways, and site. The
Other/Unknown category is heterogeneous. Site-level recalibration and
equity monitoring are recommended before deployment; race-specific
correction and fairness-weighted training were deliberately not applied.""")

D.append("## Table S11. Redevelopment sensitivity analyses\n\n" + """
Fully nested redevelopment (selection inside 10-times-repeated 5-fold outer
cross-validation; decision rule specified and archived before execution).
Deployable pool (13 candidates with harmonized definitions and >= 80%
availability in both databases): 0.718 versus 0.733 for the six-variable
model; paired difference -0.014 (95% CI -0.029 to +0.001). Symmetric pool
(lactate and urine output restored): 0.725; paired difference -0.007 (95%
CI -0.020 to +0.005). Neither met the pre-stated replacement criteria.

Outer-fold selection frequencies (source: challenger_selection.csv,
challenger_symmetric_selection.csv):

""" + md(selS) + """

The low landmark reselection of lactate (38%) and urine output (6%) is a
limitation; their retention rests on their prior selection and inclusion in
the developed model and on neither redevelopment analysis demonstrating
improved validated performance.""")

nb20 = dca.iloc[(dca['threshold'] - 0.20).abs().argmin()]
nb40 = dca.iloc[(dca['threshold'] - 0.40).abs().argmin()]

# The authored supplement lives at manuscript/SUPPLEMENT.md and is the
# document of record; this step computes the landmark threshold table and
# emits its table blocks for cross-checking, never a competing narrative.
# Additional cross-check blocks: outputs whose values reach the supplement but
# had no regenerated block, so verify_tables.py could not see them. These four
# files together held 262 of the supplement's 487 decimal values.
_extra = []
# Only files the supplement reproduces in full are listed. Files holding
# full-precision intermediates (stage_coding_robustness, dca_lm24_common) or
# values quoted selectively (locked_external_results, card_rederivation,
# reported_values) are deliberately excluded: requiring every one of their
# values to appear would fail on numbers the supplement never prints.
# Those are covered instead by verify_ledger's metric-specific checks.
for _f in ('internal_final_results.csv', 'external_incremental.csv',
           'figure1_variants_mimic.csv'):
    _p = OUT + _f
    if not _os.path.exists(_p):
        continue
    _d = pd.read_csv(_p)
    _rows = ['| ' + ' | '.join(str(c) for c in _d.columns) + ' |',
             '|' + '---|' * len(_d.columns)]
    for _, _r in _d.iterrows():
        _rows.append('| ' + ' | '.join('' if pd.isna(v) else str(v) for v in _r) + ' |')
    _extra.append('\n'.join(_rows))
D = D + _extra

open(DOC, 'w').write(
    '# Generated supplement tables (cross-check only)\n\n'
    'The document of record is manuscript/SUPPLEMENT.md. The blocks below are\n'
    'regenerated from outputs/ so table values can be diffed against it.\n\n'
    + '\n\n'.join(
        '\n'.join(ln for ln in b.split('\n') if ln.lstrip().startswith('|'))
        for b in D if '\n|' in b or b.lstrip().startswith('|')) + '\n')
print(f"generated table blocks written for cross-check "
      f"(document of record: manuscript/SUPPLEMENT.md)")
print("landmark threshold table:")
print(thr_tab.to_string(index=False))
