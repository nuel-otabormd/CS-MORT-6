"""Hospital-level heterogeneity of external discrimination (Supplementary
Table S8, panel C): the submitted analysis repeated in the primary eICU
landmark population. Frames and predictions are taken verbatim from step 06
(exec slice), so the population and frozen anion-gap model are identical to
the locked external analysis. As submitted, hospitals contributing at least
25 patients are summarized by the median, interquartile range, and range of
their AUROCs, beside the pooled AUROC.
"""
import contextlib, io
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
PIPE = _B + '/'
OUT = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'

MIN_PATIENTS = 25

src6 = open(PIPE + '06_external_descriptive.py').read()
g6 = {'__file__': PIPE + '06_external_descriptive.py'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src6.split('# ---- Within-stage cells')[0], '06_part', 'exec'), g6)
el = g6['el']
d = pd.DataFrame({'hospital': el['hospitalid'].values,
                  'y': np.asarray(g6['yl'], int),
                  'p': np.asarray(g6['p_ag_el'], float)})
assert len(d) == 1047 and d['y'].sum() == 305, (len(d), d['y'].sum())
pooled = roc_auc_score(d['y'], d['p'])
assert round(pooled, 3) == 0.748, pooled

sizes = d.groupby('hospital').size()
large = sizes[sizes >= MIN_PATIENTS].index
sub = d[d['hospital'].isin(large)]
# every qualifying hospital must contain both outcomes, or its AUROC is undefined
assert (sub.groupby('hospital')['y'].nunique() == 2).all()
auc = np.array([roc_auc_score(g['y'], g['p']) for _, g in sub.groupby('hospital')])
q1, med, q3 = np.percentile(auc, [25, 50, 75])

res = pd.DataFrame([dict(
    min_patients=MIN_PATIENTS, hospitals=len(auc), patients=len(sub),
    hospitals_in_population=int(d['hospital'].nunique()),
    median_auroc=round(med, 3), iqr_low=round(q1, 3), iqr_high=round(q3, 3),
    min_auroc=round(auc.min(), 3), max_auroc=round(auc.max(), 3),
    pooled_auroc=round(pooled, 3))])
res.to_csv(OUT + 'hospital_heterogeneity_lm24.csv', index=False)
print(res.T.to_string(header=False))
