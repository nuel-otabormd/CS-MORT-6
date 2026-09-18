"""Figure S3 data: external anion-gap calibration deciles (primary eICU
landmark population, late arrests zeroed) and calibration annotation values
for both panels (the anion-gap formulation internally and externally), with
the internal lactate values that Table 1 reports checked alongside. Frames
and predictions are taken verbatim from step 06
(exec slice), so the population and frozen model are identical to the locked
external analysis; internal panels use the canonical out-of-fold predictions.
Asserts every annotation against the published values before writing.
"""
import numpy as np, pandas as pd, statsmodels.api as sm

import os as _os
_B = _os.path.dirname(_os.path.abspath(__file__))
PIPE = _B + '/'
OUT = _os.environ.get('CSMORT6_OUT', _os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
SCRATCH = _os.environ.get('CSMORT6_DATA', _os.path.join(_B, '..', 'data')).rstrip('/') + '/'

def slope_citl_brier(p, y):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    y = np.asarray(y, int)
    lp = np.log(p / (1 - p))
    slope = sm.Logit(y, sm.add_constant(lp)).fit(disp=0).params[1]
    citl = sm.GLM(y, np.ones((len(y), 1)), offset=lp,
                  family=sm.families.Binomial()).fit().params[0]
    return slope, citl, float(np.mean((p - y) ** 2))

def deciles(p, y):
    d = pd.DataFrame({'p': p, 'y': np.asarray(y, int)})
    d['decile'] = pd.qcut(d['p'].rank(method='first'), 10, labels=False)
    g = d.groupby('decile').agg(pred=('p', 'mean'), obs=('y', 'mean'), n=('y', 'size'))
    return g.reset_index()

# ---- external: exec step 06 up to the frozen-cut panel ----
src6 = open(PIPE + '06_external_descriptive.py').read()
g6 = {'__file__': PIPE + '06_external_descriptive.py'}
exec(compile(src6.split('# ---- Within-stage cells')[0], '06_part', 'exec'), g6)
yl = np.asarray(g6['yl'], int)
p_ext = np.asarray(g6['p_ag_el'], float)
s_e, c_e, b_e = slope_citl_brier(p_ext, yl)
assert round(s_e, 2) == 1.17 and round(c_e, 2) == -0.0 and round(b_e, 3) == 0.172, (s_e, c_e, b_e)
dec_e = deciles(p_ext, yl)
dec_e.to_csv(OUT + 'external_calibration_curve_ag.csv', index=False)
print('external deciles written; slope/CITL/Brier',
      round(s_e, 2), round(c_e, 2), round(b_e, 3))

# ---- internal: canonical out-of-fold predictions ----
oof = pd.read_csv(SCRATCH + 'v2_oof_predictions.csv')
y_i = oof['y'].values.astype(int)
rows = []
for col, name, chk in [('oof_lac', 'internal_lactate', None),
                       ('oof_ag', 'internal_aniongap', (0.99, 0.00, 0.189))]:
    s, c, b = slope_citl_brier(oof[col].values, y_i)
    if chk:
        assert round(s, 2) == chk[0] and round(c, 2) == chk[1] and round(b, 3) == chk[2], (name, s, c, b)
    rows.append(dict(panel=name, slope=round(s, 2), citl=round(c, 2), brier=round(b, 3)))
assert rows[0]['slope'] == 0.99 and rows[0]['citl'] == -0.0, rows[0]
rows.append(dict(panel='external_aniongap', slope=round(s_e, 2), citl=round(c_e, 2), brier=round(b_e, 3)))
pd.DataFrame(rows).to_csv(OUT + 'calibration_annotations.csv', index=False)
print(pd.DataFrame(rows).to_string(index=False))
print('DONE')
