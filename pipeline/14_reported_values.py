"""Stage 14 - values quoted in the paper that no other step stores.

Several figures quoted in the manuscript and supplement are computed from
the frozen frames but were previously only printed, or computed outside the
pipeline: the exact-landmark availability profile, the internal
deployment-rule rescoring, the worked example, and a few derived
proportions. This step recomputes each of them from the same frames the
analysis uses and writes them to outputs/reported_values.csv, so every
value in the paper has a stored, regenerable source.

Nothing here feeds a model, a card, a band, or a threshold. It is reporting
only, and it is deliberately the last analytic step.
"""
import math
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

_B = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('CSMORT6_OUT', os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'

# Reuse step 05's frames verbatim: same cohort, same landmark, same card.
_g = {'__file__': os.path.join(_B, '05_internal_analyses.py')}
_src = open(_g['__file__']).read()
exec(compile(_src.split('# ============ 1+2.')[0], '05_partA', 'exec'), _g)
lm, y, MED, card_score = _g['lm'], _g['y'], _g['MED'], _g['card_score']

rows = []


def rec(item, value, note=''):
    rows.append(dict(item=item, value=value, note=note))
    print(f'  {item}: {value}' + (f'   [{note}]' if note else ''))


print('=' * 70)
print('14. REPORTED VALUES (exact landmark frames)')
print('=' * 70)

# ---- availability at the exact 24-hour landmark (Supplementary Table S6) ----
obs = {v: lm[v].notna() for v in ('lactate', 'aniongap', 'uo', 'bun', 'rdw')}
for v, mask in obs.items():
    rec(f'availability_{v}', f'{100 * mask.mean():.1f}')
ag_inputs = obs['aniongap'] & obs['uo'] & obs['bun'] & obs['rdw']
lac_inputs = obs['lactate'] & obs['uo'] & obs['bun'] & obs['rdw']
rec('availability_all_aniongap_model_inputs', f'{100 * ag_inputs.mean():.1f}')
rec('availability_all_lactate_model_inputs', f'{100 * lac_inputs.mean():.1f}')

# ---- internal deployment-rule rescoring (Supplementary Table S8(A)) ----
lac_missing = lm['lactate'].isna().values
rec('internal_lactate_missing_pct', f'{100 * lac_missing.mean():.1f}')
s_med = card_score(lm, MED)
ag_bands = pd.cut(lm['aniongap'].fillna(MED['aniongap']),
                  bins=[-1, 12, 18, 999], labels=False,
                  right=False).fillna(0).astype(int).values * 2
lac_bands_med = pd.cut(lm['lactate'].fillna(MED['lactate']),
                       bins=[-1, 2, 4, 999], labels=False,
                       right=False).fillna(0).astype(int).values * 2
switch = lac_missing & lm['aniongap'].notna().values
s_deploy = s_med.copy()
s_deploy[switch] = s_med[switch] - lac_bands_med[switch] + ag_bands[switch]
rec('internal_card_median_rule_auroc', f'{roc_auc_score(y, s_med):.4f}')
rec('internal_card_deployment_rule_auroc', f'{roc_auc_score(y, s_deploy):.4f}',
    'anion-gap bands where lactate is unobserved')
rec('internal_scores_changed_by_deployment_rule', int((s_deploy != s_med).sum()))

# ---- worked example (Supplementary Table S3) ----
spec = pd.read_csv(OUT + 'v2_spec_continuous.csv')
lac_spec = {r['variable']: r for _, r in spec[spec.model == 'lactate'].iterrows()}
example = {'lactate': 3.1, 'uo': 0.4, 'ohca_arrest': 0, 'age': 72, 'bun': 41, 'rdw': 15.9}
lp = float(lac_spec['(intercept)']['beta_standardized'])
for var, x in example.items():
    r = lac_spec[var]
    z = ((min(max(x, float(r['winsor_lo'])), float(r['winsor_hi'])) - float(r['mean']))
         / float(r['sd']))
    lp += float(r['beta_standardized']) * z
    rec(f'worked_example_z_{var}', f'{z:.3f}')
rec('worked_example_linear_predictor', f'{lp:.4f}')
rec('worked_example_probability', f'{1 / (1 + math.exp(-lp)):.4f}')
rec('worked_example_card_points', int(card_score(pd.DataFrame([example]), MED)[0]))
for var, x in example.items():
    rec(f'worked_example_input_{var}', x, 'illustrative input, not a result')

# ---- derived proportions quoted in prose ----
rec('landmark_outcome_proportion', f'{y.mean():.3f}')
ev = pd.read_csv(OUT + 'event_time_exact.csv').iloc[0]
after48 = int(ev['d_48_168']) + int(ev['d_gt168'])
rec('deaths_after_48h_pct', f'{100 * after48 / int(ev["total_deaths"]):.1f}')
rec('deaths_within_24h', int(ev['d_0_6']) + int(ev['d_6_12']) + int(ev['d_12_24']))
SCREEN_N, SCREEN_D = 4315, 1537      # screening extract, Supplementary Methods
rec('screening_extract_outcome_proportion', f'{SCREEN_D / SCREEN_N:.3f}',
    'archived selection extract, 4,315 ICU stays')

pd.DataFrame(rows).to_csv(OUT + 'reported_values.csv', index=False)
print(f'\n[done] reported_values.csv ({len(rows)} values)')
