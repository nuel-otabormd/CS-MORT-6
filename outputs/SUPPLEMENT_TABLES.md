# Generated supplement tables (cross-check only)

The document of record is manuscript/SUPPLEMENT.md. The blocks below are
regenerated from outputs/ so table values can be diffed against it.

| model | variable | winsor_lo | winsor_hi | impute_median | mean | sd | beta_standardized | beta_raw_scale |
|---|---|---|---|---|---|---|---|---|
| lactate | lactate | 0.7 | 12.723 | 1.9 | 2.418 | 1.8608 | 0.496888 | 0.267033 |
| lactate | uo | 0.0013 | 3.8352 | 0.728 | 0.9197 | 0.7526 | -0.427892 | -0.568569 |
| lactate | ohca_arrest | 0.0 | 1.0 | 0.0 | 0.095 | 0.2933 | 0.325232 | 1.109057 |
| lactate | age | 27.93 | 93.0 | 71.0 | 69.6641 | 14.0336 | 0.263458 | 0.018773 |
| lactate | bun | 8.0 | 122.16 | 33.0 | 39.2072 | 24.9254 | 0.254663 | 0.010217 |
| lactate | rdw | 12.2 | 24.496 | 15.2 | 15.7704 | 2.4865 | 0.198363 | 0.079777 |
| lactate | (intercept) |  |  |  |  |  | -0.806673 | -4.001369 |
| anion-gap | aniongap | 5.0 | 29.0 | 13.0 | 13.3935 | 4.5533 | 0.427884 | 0.093973 |
| anion-gap | uo | 0.0013 | 3.8352 | 0.728 | 0.9197 | 0.7526 | -0.463905 | -0.616421 |
| anion-gap | ohca_arrest | 0.0 | 1.0 | 0.0 | 0.095 | 0.2933 | 0.361791 | 1.233727 |
| anion-gap | age | 27.93 | 93.0 | 71.0 | 69.6641 | 14.0336 | 0.271008 | 0.019311 |
| anion-gap | bun | 8.0 | 122.16 | 33.0 | 39.2072 | 24.9254 | 0.082329 | 0.003303 |
| anion-gap | rdw | 12.2 | 24.496 | 15.2 | 15.7704 | 2.4865 | 0.186597 | 0.075044 |
| anion-gap | (intercept) |  |  |  |  |  | -0.82333 | -4.290575 |
| variable | points_per_level | levels |
|---|---|---|
| lactate | 2 | <2 / 2 to <4 / >=4 |
| aniongap_substitution | 2 | <12 / 12 to <18 / >=18 (when lactate unavailable) |
| uo | 1 | >=1 / 0.5 to <1 / <0.5 |
| ohca_arrest | 3 | no / yes |
| age | 1 | <65 / 65 to <80 / >=80 |
| bun | 1 | <25 / 25 to <45 / >=45 |
| rdw | 1 | <14.5 / 14.5 to <16 / >=16 |
| score | predicted_risk_pct | observed_lm24 |
|---|---|---|
| 0 | 7.2 | 5.6% (n=71) |
| 1 | 9.8 | 6.9% (n=130) |
| 2 | 13.2 | 11.2% (n=240) |
| 3 | 17.5 | 17.8% (n=314) |
| 4 | 22.9 | 24.2% (n=384) |
| 5 | 29.4 | 31.5% (n=387) |
| 6 | 36.8 | 38.2% (n=364) |
| 7 | 44.9 | 42.5% (n=294) |
| 8 | 53.3 | 54.1% (n=196) |
| 9 | 61.5 | 58.2% (n=141) |
| 10 | 69.1 | 69.2% (n=78) |
| 11 | 75.8 | 75.5% (n=53) |
| 12 | 81.4 | 81.5% (n=27) |
| 13 | 86.0 | n<10 |
| 14 | 89.6 | n<10 |
| 15 | 92.3 | n<10 |

| Metric | MIMIC-IV (n=3,103) | eICU (n=1,866; 132 hospitals) |
|---|---|---|
| Continuous, lactate | 0.778 (0.760-0.794) | 0.757 (0.733-0.780) |
| Continuous, anion gap | 0.762 (0.744-0.779) | 0.749 (0.725-0.772) |
| Integer card | 0.758 (0.740-0.774) | 0.732 (0.709-0.755) |
| Calibration, anion gap | slope 0.98 (internal) | slope 0.96, CITL +0.04 |
| BOS,MA2 head-to-head (n=1,127) | - | 0.749 vs 0.743; diff +0.006 (-0.026 to +0.038); P = .69 |

| death_before_icu | d_0_6 | d_6_12 | d_12_24 | d_24_48 | d_48_168 | d_gt168 | death_no_timestamp | total_deaths |
|---|---|---|---|---|---|---|---|---|
| 2 | 73 | 70 | 106 | 157 | 377 | 402 | 1 | 1188 |

| band | n | deaths | mortality | ci |
|---|---|---|---|---|
| Low 0-3 | 755 | 96 | 12.7 | 10.5-15.3 |
| Moderate 4-5 | 771 | 215 | 27.9 | 24.8-31.2 |
| High 6-7 | 658 | 264 | 40.1 | 36.4-43.9 |
| Very high 8-15 | 510 | 317 | 62.2 | 57.9-66.3 |
| threshold | sensitivity | specificity | PPV | NPV | LRpos | LRneg |
|---|---|---|---|---|---|---|
| >= 4 | 0.89 | 0.37 | 0.41 | 0.87 | 1.41 | 0.29 |
| >= 6 | 0.65 | 0.67 | 0.50 | 0.80 | 2.00 | 0.52 |
| >= 8 | 0.36 | 0.89 | 0.62 | 0.74 | 3.32 | 0.72 |
| >= 9 | 0.24 | 0.94 | 0.67 | 0.71 | 4.14 | 0.81 |

| cohort | stage | tertile | n | mortality | ci |
|---|---|---|---|---|---|
| MIMIC | B | Low | 168 | 16.1 | 11.3-22.4 |
| MIMIC | B | Mid | 135 | 29.6 | 22.6-37.8 |
| MIMIC | B | High | 104 | 36.5 | 27.9-46.1 |
| MIMIC | C | Low | 419 | 16.0 | 12.8-19.8 |
| MIMIC | C | Mid | 257 | 35.4 | 29.8-41.4 |
| MIMIC | C | High | 233 | 45.9 | 39.6-52.3 |
| MIMIC | D | Low | 310 | 13.2 | 9.9-17.5 |
| MIMIC | D | Mid | 202 | 26.7 | 21.1-33.2 |
| MIMIC | D | High | 187 | 57.8 | 50.6-64.6 |
| MIMIC | E | Low | 236 | 26.7 | 21.5-32.7 |
| MIMIC | E | Mid | 262 | 49.2 | 43.2-55.3 |
| MIMIC | E | High | 173 | 73.4 | 66.4-79.4 |
| eICU | B | Low | 129 | 7.0 | 3.7-12.7 |
| eICU | B | Mid | 69 | 27.5 | 18.4-39.0 |
| eICU | B | High | 66 | 36.4 | 25.8-48.4 |
| eICU | C | Low | 173 | 11.6 | 7.6-17.2 |
| eICU | C | Mid | 108 | 28.7 | 21.0-37.9 |
| eICU | C | High | 99 | 53.5 | 43.8-63.0 |
| eICU | D | Low | 73 | 8.2 | 3.8-16.8 |
| eICU | D | Mid | 44 | 15.9 | 7.9-29.4 |
| eICU | D | High | 48 | 45.8 | 32.6-59.7 |
| eICU | E | Low | 106 | 33.0 | 24.8-42.4 |
| eICU | E | Mid | 59 | 54.2 | 41.7-66.3 |
| eICU | E | High | 73 | 64.4 | 52.9-74.4 |

| scope | group | n | mortality | ci |
|---|---|---|---|---|
| all 48-h landmark | Improved (<0) | 785 | 28.9 | 25.9-32.2 |
| all 48-h landmark | Unchanged (=0) | 978 | 29.7 | 26.9-32.6 |
| all 48-h landmark | Worsened (>0) | 496 | 37.5 | 33.4-41.8 |
| intermediate 24-h score 4-7 | Improved (<0) | 429 | 24.0 | 20.2-28.3 |
| intermediate 24-h score 4-7 | Unchanged (=0) | 523 | 34.0 | 30.1-38.2 |
| intermediate 24-h score 4-7 | Worsened (>0) | 261 | 43.3 | 37.4-49.4 |

| horizon | n | lactate | bun | rdw | uo |
|---|---|---|---|---|---|
| 6.0 | 3068.0 | 69.2 | 82.6 | 80.4 | 80.9 |
| 12.0 | 2963.0 | 75.8 | 95.5 | 92.1 | 91.5 |
| 24.0 | 2731.0 | 80.8 | 99.5 | 98.9 | 94.2 |
| 48.0 | 2296.0 | 85.9 | 99.6 | 99.5 | 95.0 |

| index | lactate | aniongap | uo | age | bun | rdw |
|---|---|---|---|---|---|---|
| lactate | 1.0 | 0.53 | -0.19 | -0.0 | -0.0 | 0.06 |
| aniongap | 0.53 | 1.0 | -0.19 | 0.05 | 0.37 | 0.19 |
| uo | -0.19 | -0.19 | 1.0 | -0.15 | -0.13 | -0.06 |
| age | -0.0 | 0.05 | -0.15 | 1.0 | 0.23 | 0.07 |
| bun | -0.0 | 0.37 | -0.13 | 0.23 | 1.0 | 0.28 |
| rdw | 0.06 | 0.19 | -0.06 | 0.07 | 0.28 | 1.0 |

| subgroup | n | deaths | auroc | ci | slope | citl |
|---|---|---|---|---|---|---|
| M | 1629 | 519 | 0.748 | 0.724-0.774 | 1.07 | -0.062 |
| F | 1065 | 373 | 0.713 | 0.682-0.746 | 0.89 | 0.092 |
| White | 1687 | 537 | 0.732 | 0.706-0.757 | 1.03 | -0.067 |
| Black | 267 | 80 | 0.704 | 0.631-0.771 | 0.81 | -0.298 |
| Hispanic | 80 | 24 | 0.805 | 0.692-0.903 | 1.21 | -0.107 |
| Asian | 67 | 17 | 0.708 | 0.548-0.851 | 0.68 | -0.374 |
| Other/Unknown | 593 | 234 | 0.754 | 0.715-0.792 | 1.07 | 0.362 |

| variable | outer_fold_selection_pct |
|---|---|
| age | 100.0 |
| ohca_arrest | 100.0 |
| aniongap_h | 50.0 |
| sodium | 0.0 |
| chloride | 0.0 |
| bicarbonate | 4.0 |
| bun | 98.0 |
| rdw | 100.0 |
| creatinine | 0.0 |
| hemoglobin | 4.0 |
| sbp_min | 78.0 |
| mech_vent | 22.0 |
| pressor_count | 0.0 |
| lactate | 38.0 |
| uo | 6.0 |
