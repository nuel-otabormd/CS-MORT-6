# Generated supplement tables (cross-check only)

The document of record is manuscript/SUPPLEMENT.md. The blocks below are
regenerated from outputs/ so table values can be diffed against it.

| model | variable | winsor_lo | winsor_hi | impute_median | mean | sd | beta_standardized |
|---|---|---|---|---|---|---|---|
| lactate | lactate | 0.7 | 12.723 | 1.9 | 2.418 | 1.8608 | 0.496888 |
| lactate | uo | 0.0013 | 3.8352 | 0.728 | 0.9197 | 0.7526 | -0.427892 |
| lactate | ohca_arrest | 0.0 | 1.0 | 0.0 | 0.095 | 0.2933 | 0.325232 |
| lactate | age | 27.93 | 93.0 | 71.0 | 69.6641 | 14.0336 | 0.263458 |
| lactate | bun | 8.0 | 122.16 | 33.0 | 39.2072 | 24.9254 | 0.254663 |
| lactate | rdw | 12.2 | 24.496 | 15.2 | 15.7704 | 2.4865 | 0.198363 |
| lactate | (intercept) |  |  |  |  |  | -0.806673 |
| anion-gap | aniongap | 5.0 | 29.0 | 13.0 | 13.3935 | 4.5533 | 0.427884 |
| anion-gap | uo | 0.0013 | 3.8352 | 0.728 | 0.9197 | 0.7526 | -0.463905 |
| anion-gap | ohca_arrest | 0.0 | 1.0 | 0.0 | 0.095 | 0.2933 | 0.361791 |
| anion-gap | age | 27.93 | 93.0 | 71.0 | 69.6641 | 14.0336 | 0.271008 |
| anion-gap | bun | 8.0 | 122.16 | 33.0 | 39.2072 | 24.9254 | 0.082329 |
| anion-gap | rdw | 12.2 | 24.496 | 15.2 | 15.7704 | 2.4865 | 0.186597 |
| anion-gap | (intercept) |  |  |  |  |  | -0.82333 |
| variable | points_per_level | levels |
|---|---|---|
| lactate | 2 | <2 / 2 to <4 / >=4 |
| aniongap_substitution | 2 | <12 / 12 to <18 / >=18 (when lactate unavailable) |
| uo | 1 | >=1 / 0.5 to <1 / <0.5 |
| ohca_arrest | 3 | no / yes |
| age | 1 | <65 / 65 to <80 / >=80 |
| bun | 1 | <25 / 25 to <45 / >=45 |
| rdw | 1 | <14.5 / 14.5 to <16 / >=16 |

| Metric | MIMIC-IV (n=3,103) | eICU (1,866 stays; 132 hospitals) |
|---|---|---|
| Continuous, lactate | 0.778 (0.760-0.794) | 0.757 (0.735-0.780) |
| Continuous, anion gap | 0.762 (0.744-0.779) | 0.749 (0.726-0.772) |
| Integer card | 0.758 (0.740-0.774) | 0.732 (0.709-0.755) |
| Calibration | out-of-fold slope 0.98 (lactate formulation) | anion gap slope 0.96, CITL +0.04 |
| BOS,MA2 head-to-head (n=1,127) | - | 0.749 vs 0.743; diff +0.006 (-0.026 to +0.037); P = .69 |

| death_before_icu | d_0_6 | d_6_12 | d_12_24 | d_24_48 | d_48_168 | d_gt168 | death_no_timestamp | total_deaths |
|---|---|---|---|---|---|---|---|---|
| 2 | 73 | 70 | 106 | 157 | 377 | 402 | 1 | 1188 |

| band | mortality |
|---|---|
| Low 0-3 | 12.7 |
| Moderate 4-5 | 27.9 |
| High 6-7 | 40.1 |
| Very high 8-15 | 62.2 |
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

| subgroup | n | deaths | auroc | ci | slope | citl |
|---|---|---|---|---|---|---|
| M | 1629 | 519 | 0.748 | 0.724-0.774 | 1.07 | -0.062 |
| F | 1065 | 373 | 0.713 | 0.682-0.746 | 0.89 | 0.092 |
| White | 1687 | 537 | 0.732 | 0.706-0.757 | 1.03 | -0.067 |
| Black | 267 | 80 | 0.704 | 0.631-0.771 | 0.81 | -0.298 |
| Hispanic | 80 | 24 | 0.805 | 0.692-0.903 | 1.21 | -0.107 |
| Asian | 67 | 17 | 0.708 | 0.548-0.851 | 0.68 | -0.374 |
| Other/Unknown | 593 | 234 | 0.754 | 0.715-0.792 | 1.07 | 0.362 |

| section | item | value |
|---|---|---|
| lm48 | n / deaths / mortality | 2259 / 703 / 31.1% |
| lm48 | continuous lactate updated-48h | AUROC 0.739 (0.717-0.760), slope 1.10, CITL +0.028 |
| lm48 | continuous lactate stale-24h | AUROC 0.714 (0.692-0.736), slope 0.91, CITL -0.057 |
| lm48 | integer stale vs updated AUROC | 0.700 vs 0.726 |
| trajectory | all 48-h landmark | Improved (<0) | n=785 mortality 28.9% (25.9-32.2) |
| trajectory | all 48-h landmark | Unchanged (=0) | n=978 mortality 29.7% (26.9-32.6) |
| trajectory | all 48-h landmark | Worsened (>0) | n=496 mortality 37.5% (33.4-41.8) |
| trajectory | intermediate 24-h score 4-7 | Improved (<0) | n=429 mortality 24.0% (20.2-28.3) |
| trajectory | intermediate 24-h score 4-7 | Unchanged (=0) | n=523 mortality 34.0% (30.1-38.2) |
| trajectory | intermediate 24-h score 4-7 | Worsened (>0) | n=261 mortality 43.3% (37.4-49.4) |
| trajectory | aOR per +1 change (adj 24-h score) | 1.37 (1.27-1.47), p=1.7e-17 |
| event-time | buckets 0-6/6-12/12-24/24-48h | 73/70/106/157 |
| event-time | 48h-7d / >7d | 377 / 402 |
| event-time | anomalies (disclosed) | 2 recorded before ICU admission, 1 without timestamp |
| vif | lactate model | lactate 1.05  uo 1.08  ohca_arrest 1.02  age 1.08  bun 1.16  rdw 1.10 |
| vif | anion-gap model | aniongap 1.22  uo 1.06  ohca_arrest 1.01  age 1.08  bun 1.31  rdw 1.11 |
| vif | key Pearson r | lactate-bun -0.0, lactate-rdw 0.06, bun-rdw 0.28, aniongap-bun 0.37 |
| imputation | median | AUROC 0.734, slope 0.99, CITL -0.000 |
| imputation | mice | AUROC 0.725, slope 1.01, CITL +0.001 |
| sensitivity | ICD-confirmed only | n=2452 mort 33.2% cont 0.734 integer 0.727 |
| sensitivity | Sepsis-3 excluded | n=1321 mort 28.2% cont 0.747 integer 0.739 |
| sensitivity | non-OHCA subgroup | n=2438 mort 30.8% cont 0.724 integer 0.712 |
| sensitivity | OHCA-free score (all LM24) | cont n/a integer 0.711 |
| fairness | M | n=1629 deaths=519 AUROC 0.748 (0.724-0.774) slope 1.07 CITL -0.062 |
| fairness | F | n=1065 deaths=373 AUROC 0.713 (0.682-0.746) slope 0.89 CITL +0.092 |
| fairness | White | n=1687 deaths=537 AUROC 0.732 (0.706-0.757) slope 1.03 CITL -0.067 |
| fairness | Black | n=267 deaths=80 AUROC 0.704 (0.631-0.771) slope 0.81 CITL -0.298 |
| fairness | Hispanic | n=80 deaths=24 AUROC 0.805 (0.692-0.903) slope 1.21 CITL -0.107 |
| fairness | Asian | n=67 deaths=17 AUROC 0.708 (0.548-0.851) slope 0.68 CITL -0.374 |
| fairness | Other/Unknown | n=593 deaths=234 AUROC 0.754 (0.715-0.792) slope 1.07 CITL +0.362 |
| cvauc | CV AUROC (fold mean) with IC-based 95% CI | 0.7339 (0.7140-0.7538); pooled bootstrap for comparison 0.7337 (0.7143-0.7527) |
| scai | stage-only / score-only / stage+score AUROC | 0.589 / 0.727 / 0.728 |
| scai | LRT score over stage | chi2 348.2, p 1.0e-77 |
| scai | paired dAUROC (stage+score - stage) | +0.139 (+0.116 to +0.163) |
| scai | incremental continuous AG (matched) | stage 0.589 / score 0.726 / both 0.728; +0.139 (+0.116 to +0.162); LRT p=1.8e-77 |
| scai | incremental continuous AG, stage without arrest rule | stage 0.564 / score 0.726 / both 0.728; +0.165 (+0.140 to +0.190); LRT p=7.4e-85 |
| scai | incremental integer card, stage without arrest rule | stage 0.564 / score 0.727 / both 0.728; +0.164 (+0.140 to +0.189); LRT p=6.8e-84 |
| scai | stage B within-stage AUROC | n=407 0.636 (0.579-0.692) |
| scai | stage C within-stage AUROC | n=909 0.689 (0.651-0.724) |
| scai | stage D within-stage AUROC | n=699 0.756 (0.717-0.793) |
| scai | stage E within-stage AUROC | n=671 0.728 (0.689-0.765) |
| scai | ohca-free tertile mortality by stage | B 16/30/37; C 16/35/46; D 13/27/58; E 30/49/73 |
| scai | non-staging tertile mortality by stage | B 16/32/36; C 15/32/46; D 12/34/53; E 35/51/68 |
| availability | 6h (n=3068) | lactate 69.2%  bun 82.6%  rdw 80.4%  uo 80.9% |
| availability | 12h (n=2963) | lactate 75.8%  bun 95.5%  rdw 92.1%  uo 91.5% |
| availability | 24h (n=2731) | lactate 80.8%  bun 99.5%  rdw 98.9%  uo 94.2% |
| availability | 48h (n=2296) | lactate 85.9%  bun 99.6%  rdw 99.5%  uo 95.0% |

| item | value |
|---|---|
| stage_auroc | 0.613 |
| score_auroc_continuousAG | 0.748 |
| both_auroc_continuousAG | 0.754 |
| score_over_stage_continuousAG | +0.141 (+0.101 to +0.178) |
| lrt_chi2_p_continuousAG | 142.3, 8.4e-33 |
| stage_over_score_continuousAG | +0.006 |
| incremental_integer_hybrid | stage 0.613 / score 0.759 / both 0.767; +0.154 (+0.116 to +0.191); LRT p=7.1e-36 |
| incremental_continuousAG_stage_no_arrest_rule | stage 0.524 / score 0.748 / both 0.750; +0.226 (+0.179 to +0.272); LRT p=1.6e-40 |
| incremental_integer_hybrid_stage_no_arrest_rule | stage 0.524 / score 0.759 / both 0.761; +0.237 (+0.193 to +0.283); LRT p=8.4e-43 |
