"""External risk-category mortality under both integer-score rules
(Supplementary Table S7, panel B): the deployment rule (lactate categories
when lactate was measured, anion-gap categories otherwise) and anion-gap
categories for every patient, as the submitted table reported both. The
population and card are taken verbatim from step 04 (exec slice), and the
deployment-rule rows must reproduce the locked external run before anything
is written.
"""
import contextlib, io
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
PIPE = _B + '/'
OUT = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'

src4 = open(PIPE + '04_external_validation.py').read()
cut = src4.index('el = e24[LM]; yl = ye[LM]')
cut = src4.index('\n', cut) + 1
g4 = {'__file__': PIPE + '04_external_validation.py'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src4[:cut], '04_part', 'exec'), g4)
el, yl, card, wilson = g4['el'], np.asarray(g4['yl'], int), g4['card_score'], g4['wilson']
assert len(el) == 1047 and yl.sum() == 305, (len(el), yl.sum())

rules = {'deployment rule': card(el, ag_for_lactate='hybrid'),
         'anion gap for all': card(el, ag_for_lactate=True)}
assert round(roc_auc_score(yl, rules['deployment rule']), 3) == 0.759
assert round(roc_auc_score(yl, rules['anion gap for all']), 3) == 0.738

BANDS = [(-1, 3, 'Low', '0-3'), (3, 5, 'Moderate', '4-5'), (5, 7, 'High', '6-7'), (7, 15, 'Very high', '8-15')]
rows = []
for rule, s in rules.items():
    for lo, hi, band, span in BANDS:
        mk = (s > lo) & (s <= hi)
        n, d = int(mk.sum()), int(yl[mk].sum())
        wlo, whi = wilson(d, n)
        rows.append(dict(rule=rule, band=band, score=span, n=n, deaths=d,
                         mortality_pct=round(100 * d / n, 1), ci_low=round(wlo, 1), ci_high=round(whi, 1)))
res = pd.DataFrame(rows)

locked = pd.read_csv(OUT + 'locked_external_results.csv')
for r in res[res['rule'] == 'deployment rule'].itertuples():
    value = locked.loc[(locked['frame'] == 'LM24') & (locked['item'] == f'band {r.band} {r.score}'), 'value'].iloc[0]
    assert value == f'n={r.n} mortality {r.mortality_pct:.1f}% ({r.ci_low:.1f}-{r.ci_high:.1f})', (r.band, value)

res.to_csv(OUT + 'external_risk_bands_lm24.csv', index=False)
print(res.to_string(index=False))
