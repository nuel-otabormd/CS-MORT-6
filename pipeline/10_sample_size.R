# Minimum development sample size for the landmark model (Riley et al criteria,
# pmsampsize). Conservative anticipated C-statistic 0.70, outcome proportion
# 0.331 (892/2,694 at the 24-hour landmark), six predictor parameters.
if (!requireNamespace("pmsampsize", quietly = TRUE))
  install.packages("pmsampsize", repos = "https://cloud.r-project.org")
library(pmsampsize)
print(pmsampsize(type = "b", cstatistic = 0.70, parameters = 6, prevalence = 0.331))
