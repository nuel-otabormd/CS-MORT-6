# Figure renderer: Figure 1 and Supplementary Figures S1-S7, 300 dpi.
# Every plotted value is read from the canonical outputs/ CSVs. The only
# hand-entered numbers are the S1 flow counts, each traceable: 4,315 / 3,103
# re-verified from the screening extract (in_primary_cohort sums to 3,103);
# the 226 / 986 exclusion split is the submitted Figure S1 chain (cohort
# unchanged in revision); landmark decompositions from Table S2 (251/156/2)
# and the amendment (1,586 -> 1,047, difference 539).
.B   <- dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)[1]))
OUT  <- paste0(Sys.getenv("CSMORT6_OUT", file.path(.B, "..", "outputs")), "/")
FIG  <- paste0(Sys.getenv("CSMORT6_FIG", file.path(.B, "..", "figures")), "/")
dir.create(FIG, showWarnings = FALSE)
BLU  <- c("#D7E6F4", "#6BAED6", "#14548C")
ORG  <- "#E8821E"; NAVY <- "#1F4E79"; LBLU <- "#7EB3E3"
GRID <- "#E4E4E4"; AXCOL <- "#333333"

pci <- function(s) as.numeric(strsplit(s, "-")[[1]])
wilson <- function(k, n, z = 1.959964) {
  p <- k / n; d <- 1 + z^2 / n
  c((p + z^2/(2*n) - z*sqrt(p*(1-p)/n + z^2/(4*n^2))) / d,
    (p + z^2/(2*n) + z*sqrt(p*(1-p)/n + z^2/(4*n^2))) / d)
}
open_png <- function(f, w, h) png(file.path(FIG, f), width = w, height = h,
                                  units = "in", res = 300)

# ---------- grouped-bar panel (Figure 1, S4, S5) ----------
bar_panel <- function(d, title, ylim, stages, legend = FALSE,
                      ylab = "In-hospital mortality (%)", group_lab = "Stage",
                      legend_title = "CS-MORT-6 score", letter = NULL) {
  n_s <- length(stages); xl <- c(0.5, n_s + 0.5)
  plot(NA, xlim = xl, ylim = ylim, axes = FALSE, xlab = "", ylab = "",
       xaxs = "i", yaxs = "i")
  yt <- pretty(ylim); yt <- yt[yt >= ylim[1] & yt <= ylim[2]]
  abline(h = yt[yt > 0], col = GRID, lwd = 0.9)
  bw <- 0.26; off <- c(-bw, 0, bw)
  for (i in seq_len(n_s)) {
    ds <- d[d$stage == stages[i], ]
    for (j in 1:3) {
      r <- ds[j, ]
      x0 <- i + off[j] - bw/2; x1 <- i + off[j] + bw/2
      rect(x0, 0, x1, r$mortality, col = BLU[j], border = "white", lwd = 0.8)
      ci <- pci(r$ci)
      segments(i + off[j], ci[1], i + off[j], ci[2], lwd = 1.6, col = "#333333")
      segments(i + off[j] - 0.05, ci, i + off[j] + 0.05, ci, lwd = 1.6, col = "#333333")
    }
    mtext(paste(group_lab, stages[i]), side = 1, line = 0.4, at = i, cex = 0.85)
  }
  axis(2, at = yt, las = 1, lwd = 0, lwd.ticks = 1, cex.axis = 0.95, col.ticks = AXCOL)
  mtext(ylab, side = 2, line = 2.6, cex = 0.95)
  u <- par("usr")
  if (!is.null(letter))
    mtext(letter, side = 3, line = 0.45, at = u[1], adj = 0, font = 2, cex = 1.25)
  mtext(title, side = 3, line = 0.45, at = u[1] + (u[2] - u[1]) * (if (is.null(letter)) 0 else 0.075),
        adj = 0, font = 1, cex = 1.0)
  box(bty = "l", col = AXCOL)
  if (legend)
    legend("topleft", inset = c(0.01, 0.02), fill = BLU, border = "white",
           legend = c("Low tertile", "Mid tertile", "High tertile"),
           title = legend_title, title.adj = 0, bty = "n", cex = 0.95)
}

# ================= FIGURE 1 =================
f1m <- read.csv(paste0(OUT, "figure1_mimic_lm24.csv"))
f1e <- read.csv(paste0(OUT, "figure1_eicu_lm24.csv"))
png(file.path(FIG, "Figure1.png"), width = 7.48, height = 3.55, units = "in",
    res = 600, pointsize = 8)
par(mfrow = c(1, 2), mar = c(2.6, 4.2, 2.2, 0.8), family = "sans")
bar_panel(f1m, "MIMIC-IV (development)", c(0, 90), c("B", "C", "D", "E"),
          legend = TRUE, letter = "A")
bar_panel(f1e, "eICU (external)", c(0, 90), c("B", "C", "D", "E"), letter = "B")
dev.off()
# Figure1.tif for the journal is converted from Figure1.png (identical
# pixels) with LZW compression by pipeline packaging (PIL), keeping 300 dpi.
cat("Figure1 cells MIMIC:", paste(f1m$mortality, collapse = " "), "\n")
cat("Figure1 cells eICU:", paste(f1e$mortality, collapse = " "), "\n")

# ================= FIGURE S1 (flow) =================
rrect <- function(x0, y0, x1, y1, fill = "white", border = "#555555") {
  rect(x0, y0, x1, y1, col = fill, border = border, lwd = 1.6)
}
LH <- 0.030; PAD <- 0.014
fbox2 <- function(cx, ytop, w, lines, fill = "white", cex = 0.8, font = 1) {
  h <- length(lines) * LH + PAD
  rrect(cx - w/2, ytop - h, cx + w/2, ytop, fill = fill)
  for (i in seq_along(lines))
    text(cx, ytop - PAD/2 - (i - 0.5) * LH, lines[i], cex = cex, font = font)
  ytop - h
}
arrow_v <- function(x, y0, y1) arrows(x, y0, x, y1, length = 0.09, lwd = 1.8, col = "#555555")
open_png("FigS1.png", 10.5, 7.4)
par(mar = c(0, 0, 0, 0), family = "sans")
plot(NA, xlim = c(0, 1), ylim = c(0.04, 1), axes = FALSE, xlab = "", ylab = "")
text(0.235, 0.985, "MIMIC-IV (development)", font = 2, cex = 1.1)
text(0.79, 0.985, "eICU-CRD (external validation)", font = 2, cex = 1.1)
XM <- 0.235; WM <- 0.43          # MIMIC column
XX <- 0.45;  WX <- 0.30          # exclusion boxes (right edge 0.60)
XE <- 0.795; WE <- 0.37          # eICU column (left edge 0.61)
gap2 <- 2 * LH + PAD + 0.024     # gap holding a 2-line exclusion box
gap5 <- 5 * LH + PAD + 0.024     # gap holding a 5-line exclusion box
y <- 0.955
b1 <- fbox2(XM, y, WM, c("Adult ICU stays with documented cardiogenic",
      "shock (diagnostic code or affirmed",
      "discharge-summary documentation)", "n = 4,315"))
arrow_v(XM, b1, b1 - gap2); mid <- b1 - gap2/2
fbox2(XX, mid + (2*LH+PAD)/2, WX, c("Excluded: no objective shock",
      "criterion within 24 h (n = 226)"), fill = "#EFEFEF", cex = 0.74)
segments(XM, mid, XX - WX/2, mid, lwd = 1.6, col = "#555555")
b2 <- fbox2(XM, b1 - gap2, WM, c("Documented cardiogenic shock with at least",
      "one objective hypoperfusion criterion within 24 h", "n = 4,089"))
arrow_v(XM, b2, b2 - gap2); mid <- b2 - gap2/2
fbox2(XX, mid + (2*LH+PAD)/2, WX, c("Excluded: non-index ICU stay,",
      "one admission per patient (n = 986)"), fill = "#EFEFEF", cex = 0.74)
segments(XM, mid, XX - WX/2, mid, lwd = 1.6, col = "#555555")
b3 <- fbox2(XM, b2 - gap2, WM, c("Development cohort",
      "n = 3,103 (in-hospital mortality 38.3%)"), fill = "#DCE9F5", font = 2)
arrow_v(XM, b3, b3 - gap5); mid <- b3 - gap5/2
fbox2(XX, mid + (5*LH+PAD)/2, WX, c("Excluded at 24 h (n = 409):",
      "251 death at or before 24 h",
      "(2 pre-ICU timestamps)",
      "156 discharged alive before 24 h",
      "2 indeterminate ICU discharge times"), fill = "#EFEFEF", cex = 0.72)
segments(XM, mid, XX - WX/2, mid, lwd = 1.6, col = "#555555")
b4 <- fbox2(XM, b3 - gap5, WM - 0.04, c("Landmark population",
      "(alive and in the ICU at 24 hours)",
      "n = 2,694 (mortality 33.1%)"), fill = "#DCE9F5", font = 2)
y <- 0.955
e1 <- fbox2(XE, y, WE, c("ICU stays with a cardiogenic-shock",
      "diagnosis entry", "n = 1,866 (132 hospitals)"))
arrow_v(XE, e1, e1 - 0.05)
e2 <- fbox2(XE, e1 - 0.05, WE, c("Landmark stays",
      "(alive and in the ICU at 24 hours)", "n = 1,586 (1,439 unique patients)"))
arrow_v(XE, e2, e2 - 0.05)
e3 <- fbox2(XE, e2 - 0.05, WE, c("Excluded (n = 539): shock first documented",
      "after 24 h, or not the patient's",
      "first qualifying stay"), fill = "#EFEFEF", cex = 0.74)
arrow_v(XE, e3, e3 - 0.05)
e4 <- fbox2(XE + 0.015, e3 - 0.05, WE, c("Primary external population",
      "(first qualifying stay per patient,",
      "shock documented by 24 h)",
      "n = 1,047 (mortality 29.1%, 117 hospitals)"), fill = "#DCE9F5", font = 2)
text(0.5, 0.085, "Day-1 all-admissions analyses use the 1,866-stay cohort; the 1,586-stay and",
     cex = 0.78, col = "#444444")
text(0.5, 0.055, "1,439-patient populations are reported as sensitivity analyses.",
     cex = 0.78, col = "#444444")
dev.off()

# ================= FIGURE S2 (calibration) =================
ann <- read.csv(paste0(OUT, "calibration_annotations.csv"))
cal_panel <- function(d, col, letter, lab, an) {
  plot(NA, xlim = c(0, 1), ylim = c(0, 1), axes = FALSE, xlab = "", ylab = "",
       xaxs = "i", yaxs = "i")
  abline(h = seq(0.2, 1, 0.2), col = GRID, lwd = 0.8)
  abline(0, 1, lty = 2, col = "#999999", lwd = 1.6)
  for (i in seq_len(nrow(d))) {
    k <- round(d$obs[i] * d$n[i]); ci <- wilson(k, d$n[i])
    segments(d$pred[i], ci[1], d$pred[i], ci[2], col = col, lwd = 1.8)
  }
  points(d$pred, d$obs, pch = 21, bg = "white", col = col, lwd = 2.2, cex = 1.3)
  axis(1, at = seq(0, 1, 0.2), cex.axis = 0.9, col = AXCOL)
  axis(2, at = seq(0, 1, 0.2), las = 1, cex.axis = 0.9, col = AXCOL)
  box(bty = "l", col = AXCOL)
  mtext("Predicted probability", side = 1, line = 2.2, cex = 0.75)
  mtext("Observed mortality", side = 2, line = 2.6, cex = 0.75)
  text(0.02, 0.965, letter, font = 2, cex = 1.3, adj = 0)
  text(0.98, 0.10, lab, adj = 1, cex = 0.85, col = "#333333")
  text(0.98, 0.045, sprintf("slope %.2f   CITL %.2f   Brier %.3f",
       an$slope, abs(an$citl) * ifelse(an$citl < 0, -1, 1), an$brier),
       adj = 1, cex = 0.85, col = "#333333")
}
cl <- read.csv(paste0(OUT, "v2_calibration_curve_oof_lac.csv"))
ca <- read.csv(paste0(OUT, "v2_calibration_curve_oof_ag.csv"))
ce <- read.csv(paste0(OUT, "external_calibration_curve_ag.csv"))
open_png("FigS2.png", 12.6, 4.4)
par(mfrow = c(1, 3), mar = c(3.4, 3.8, 1.0, 0.8), family = "sans")
cal_panel(cl, "#2C6FA8", "A", "MIMIC-IV out-of-fold, lactate formulation",
          ann[ann$panel == "internal_lactate", ])
cal_panel(ca, "#2C6FA8", "B", "MIMIC-IV out-of-fold, anion-gap formulation",
          ann[ann$panel == "internal_aniongap", ])
cal_panel(ce, ORG, "C", "eICU external, anion-gap formulation",
          ann[ann$panel == "external_aniongap", ])
dev.off()

# ================= FIGURE S3 (decision curves) =================
dca <- read.csv(paste0(OUT, "dca_lm24_common.csv"))
open_png("FigS3.png", 9.5, 6.8)
par(mar = c(4.0, 4.4, 1.0, 0.8), family = "sans")
yl <- c(-0.05, 1.02 * max(c(dca$cs_mort6_ag, dca$bosma2_published,
                            dca$bosma2_recal, dca$treat_all)))
plot(NA, xlim = c(5, 70), ylim = yl, axes = FALSE, xlab = "", ylab = "")
abline(h = pretty(yl), col = GRID, lwd = 0.8)
x <- dca$threshold * 100
lines(x, dca$treat_all, col = "#8C8C8C", lwd = 2)
abline(h = 0, lty = 2, col = "#8C8C8C", lwd = 1.6)
lines(x, dca$bosma2_recal, col = LBLU, lwd = 2.4, lty = 3)
lines(x, dca$bosma2_published, col = NAVY, lwd = 2.4, lty = 2)
lines(x, dca$cs_mort6_ag, col = ORG, lwd = 3)
axis(1, cex.axis = 0.95, col = AXCOL); axis(2, las = 1, cex.axis = 0.95, col = AXCOL)
box(bty = "l", col = AXCOL)
mtext("Threshold probability (%)", side = 1, line = 2.4)
mtext("Net benefit", side = 2, line = 3.0)
legend("topright", bty = "n", cex = 0.95, lwd = c(2, 1.6, 3, 2.4, 2.4),
       lty = c(1, 2, 1, 2, 3), col = c("#8C8C8C", "#8C8C8C", ORG, NAVY, LBLU),
       legend = c("Treat all", "Treat none", "CS-MORT-6 (anion gap, frozen)",
                  "BOS,MA2 (published, frozen)", "BOS,MA2 (recalibrated, in-sample)"))
text(69, yl[1] + 0.72 * diff(yl), "Common-scorable landmark set\n(n = 654, 30.0% mortality)",
     adj = 1, cex = 0.9, col = "#333333")
dev.off()

# ================= FIGURE S4 (variants) =================
v <- read.csv(paste0(OUT, "figure1_variants_mimic.csv"))
vn <- unique(v$variant)
lab4 <- ifelse(grepl("ohca", vn), "Arrest-free card",
               "Four-variable non-staging sub-score")
open_png("FigS4.png", 12, 5.6)
par(mfrow = c(1, 2), mar = c(2.6, 4.2, 2.2, 0.8), family = "sans")
bar_panel(v[v$variant == vn[1], ], paste0("MIMIC-IV, ", tolower(substr(lab4[1],1,1)), substr(lab4[1],2,99)), c(0, 90),
          c("B", "C", "D", "E"), legend = TRUE, legend_title = "Score tertile", letter = "A")
bar_panel(v[v$variant == vn[2], ], paste0("MIMIC-IV, ", tolower(substr(lab4[2],1,1)), substr(lab4[2],2,99)), c(0, 90),
          c("B", "C", "D", "E"), letter = "B")
dev.off()
cat("FigS4 variants:", vn, "\n")

# ================= FIGURE S5 (trajectory) =================
tr <- read.csv(paste0(OUT, "trajectory_symmetric.csv"))
tr$stage <- sub(" .*", "", tr$group)          # Improved / Unchanged / Worsened
sc <- unique(tr$scope)
tr_panel <- function(d, title, legend = FALSE, letter = NULL) {
  d$stage <- factor(d$stage, levels = c("Improved", "Unchanged", "Worsened"))
  d <- d[order(d$stage), ]
  plot(NA, xlim = c(0.4, 3.6), ylim = c(0, 60), axes = FALSE, xlab = "",
       ylab = "", xaxs = "i", yaxs = "i")
  abline(h = seq(10, 60, 10), col = GRID, lwd = 0.9)
  for (j in 1:3) {
    rect(j - 0.3, 0, j + 0.3, d$mortality[j], col = BLU[j], border = NA)
    ci <- pci(d$ci[j])
    segments(j, ci[1], j, ci[2], lwd = 1.6)
    segments(j - 0.06, ci, j + 0.06, ci, lwd = 1.6)
    mtext(paste0(d$stage[j], "\nn = ", format(d$n[j], big.mark = ",")),
          side = 1, line = 1.7, at = j, cex = 0.75)
  }
  axis(2, at = seq(0, 60, 10), las = 1, lwd = 0, lwd.ticks = 1, cex.axis = 0.95, col.ticks = AXCOL)
  mtext("In-hospital mortality (%)", side = 2, line = 2.6, cex = 0.95)
  u <- par("usr")
  if (!is.null(letter))
    mtext(letter, side = 3, line = 0.4, at = u[1], adj = 0, font = 2, cex = 1.2)
  mtext(title, side = 3, line = 0.4, at = u[1] + (u[2] - u[1]) * (if (is.null(letter)) 0 else 0.08),
        adj = 0, font = 1, cex = 1.0)
  box(bty = "l", col = AXCOL)
}
open_png("FigS5.png", 11, 5.2)
par(mfrow = c(1, 2), mar = c(4.4, 4.2, 2.2, 0.8), family = "sans")
tr_panel(tr[tr$scope == sc[1], ], "All 48-hour landmark patients", letter = "A")
tr_panel(tr[tr$scope == sc[2], ], "Intermediate 24-hour score subgroup", letter = "B")
dev.off()
cat("FigS5 scopes:", sc, "\n")

# ================= FIGURE S6 (subgroups) =================
fs <- read.csv(paste0(OUT, "fairness_subgroups_lm24.csv"))
fs$label <- fs$subgroup
fs$label[fs$label == "M"] <- "Male"; fs$label[fs$label == "F"] <- "Female"
fs <- fs[nrow(fs):1, ]                       # top-down display order
open_png("FigS6.png", 12, 5.0)
par(mfrow = c(1, 2), mar = c(4.2, 8.2, 2.4, 1.0), family = "sans")
yy <- seq_len(nrow(fs))
plot(NA, xlim = c(0.48, 0.95), ylim = c(0.5, nrow(fs) + 0.5), axes = FALSE,
     xlab = "", ylab = "")
abline(v = 0.5, lty = 3, col = "#888888")
for (i in yy) {
  ci <- pci(fs$ci[i])
  segments(ci[1], i, ci[2], i, lwd = 1.8)
  segments(ci, i - 0.1, ci, i + 0.1, lwd = 1.8)
}
points(fs$auroc, yy, pch = 21, bg = "#2C6FA8", col = "#2C6FA8",
       cex = 1.1 + 2.4 * sqrt(fs$deaths / max(fs$deaths)))
axis(1, at = seq(0.5, 0.9, 0.1), cex.axis = 0.95, col = AXCOL)
axis(2, at = yy, labels = fs$label, las = 1, lwd = 0, cex.axis = 1.0)
box(bty = "l", col = AXCOL)
mtext("Subgroup AUROC (95% CI)", side = 1, line = 2.4, cex = 0.95)
mtext("A   Discrimination", side = 3, line = 0.6, adj = 0, font = 2, cex = 1.1)
legend("topright", inset = c(0.0, 0.0), bty = "n", cex = 0.8,
       pt.cex = 1.1 + 2.4 * sqrt(c(100, 300, 500) / max(fs$deaths)),
       pch = 21, pt.bg = "#2C6FA8", col = "#2C6FA8",
       legend = c("100 deaths", "300", "500"), y.intersp = 1.7)
plot(NA, xlim = c(-0.45, 0.45), ylim = c(0.5, nrow(fs) + 0.5), axes = FALSE,
     xlab = "", ylab = "")
abline(v = 0, lty = 2, col = "#888888")
segments(0, yy, fs$citl, yy, col = "#BBBBBB", lwd = 2.2)
points(fs$citl, yy, pch = 19, cex = 1.5,
       col = ifelse(abs(fs$citl) >= 0.25, "#D2691E", "#1B9E77"))
axis(1, at = seq(-0.4, 0.4, 0.2), cex.axis = 0.95, col = AXCOL)
axis(2, at = yy, labels = fs$label, las = 1, lwd = 0, cex.axis = 1.0)
box(bty = "l", col = AXCOL)
mtext("Calibration-in-the-large", side = 1, line = 2.4, cex = 0.95)
mtext("B   Calibration", side = 3, line = 0.6, adj = 0, font = 2, cex = 1.1)
dev.off()
cat("FigS6 rows:", paste(fs$label, collapse = ", "), "\n")

# ================= FIGURE S7 (nomogram, anion-gap model) =================
sp <- read.csv(paste0(OUT, "v2_spec_continuous.csv"))
ag <- sp[sp$model == "anion-gap" & sp$variable != "(intercept)", ]
ic <- sp[sp$model == "anion-gap" & sp$variable == "(intercept)", "beta_raw_scale"]
vars <- data.frame(
  var = c("aniongap", "uo", "ohca_arrest", "age", "bun", "rdw"),
  name = c("Anion gap, mmol/L", "Urine output, mL/kg/h",
           "Cardiac arrest at presentation", "Age, years",
           "Blood urea nitrogen, mg/dL", "Red cell distribution width, %"))
ag <- merge(vars, ag, by.x = "var", by.y = "variable", sort = FALSE)
ag$lo <- ag$winsor_lo; ag$hi <- ag$winsor_hi
ag$best <- ifelse(ag$beta_raw_scale > 0, ag$lo, ag$hi)
ag$range <- abs(ag$beta_raw_scale) * (ag$hi - ag$lo)
mx <- max(ag$range)
pts_of <- function(row, x) abs(row$beta_raw_scale) * abs(x - row$best) / mx * 100
TICKS <- list(
  aniongap = list(at = c(5, 10, 15, 20, 25, 29),
                  lab = c("5", "10", "15", "20", "25", "29")),
  uo  = list(at = c(3.8352, 3.5, 3, 2.5, 2, 1.5, 1, 0.5, 0.0013),
             lab = c("", "3.5", "3", "2.5", "2", "1.5", "1", "0.5", "")),
  age = list(at = c(27.93, 30, 40, 50, 60, 70, 80, 90, 93),
             lab = c("", "30", "40", "50", "60", "70", "80", "90", "")),
  bun = list(at = c(8, 20, 40, 60, 80, 100, 120, 122.16),
             lab = c("8", "", "", "", "", "", "120", "")),
  rdw = list(at = c(12.2, 14, 16, 18, 20, 22, 24, 24.496),
             lab = c("", "14", "16", "18", "20", "22", "24", "")))
base_lp <- ic + sum(ag$beta_raw_scale * ag$best)
# self-check: three profiles, direct lp vs points-mapped lp
for (k in 1:3) {
  set.seed(k)
  xs <- ag$lo + runif(6) * (ag$hi - ag$lo)
  lp_direct <- ic + sum(ag$beta_raw_scale * xs)
  tp <- sum(mapply(function(i, x) pts_of(ag[i, ], x), seq_len(6), xs))
  lp_pts <- base_lp + tp / 100 * mx
  stopifnot(abs(lp_direct - lp_pts) < 1e-9)
}
open_png("FigS7.png", 10.5, 7.2)
par(mar = c(1.5, 12.5, 1.5, 1.5), family = "sans")
nrows <- 6 + 2
plot(NA, xlim = c(0, 100), ylim = c(0.4, nrows + 1.2), axes = FALSE,
     xlab = "", ylab = "")
yrow <- nrows + 0.6
axis(3, at = seq(0, 100, 10), pos = yrow, cex.axis = 0.85, col = AXCOL, tcl = -0.25)
mtext("Points", side = 2, at = yrow, las = 1, line = 0.5, cex = 0.95, font = 2)
for (i in seq_len(6)) {
  r <- ag[i, ]; y <- nrows - i + 0.6
  mtext(r$name, side = 2, at = y, las = 1, line = 0.5, cex = 0.9)
  if (r$var == "ohca_arrest") {
    p0 <- pts_of(r, 0); p1 <- pts_of(r, 1)
    segments(min(p0, p1), y, max(p0, p1), y, lwd = 1.4, col = AXCOL)
    for (vv in c(0, 1)) {
      pp <- pts_of(r, vv)
      segments(pp, y - 0.06, pp, y + 0.06, lwd = 1.4, col = AXCOL)
      text(pp, y + 0.22, ifelse(vv == 0, "No", "Yes"), cex = 0.75)
    }
  } else {
    tk <- TICKS[[r$var]]
    pp <- sapply(tk$at, function(x) pts_of(r, x))
    segments(min(pp), y, max(pp), y, lwd = 1.4, col = AXCOL)
    segments(pp, y - 0.06, pp, y + 0.06, lwd = 1.4, col = AXCOL)
    show <- tk$lab != ""
    text(pp[show], y + 0.22, tk$lab[show], cex = 0.72)
  }
}
y_tp <- 1.6
tp_max <- ceiling(sum(sapply(seq_len(6), function(i)
  max(pts_of(ag[i, ], ag$lo[i]), pts_of(ag[i, ], ag$hi[i])))) / 10) * 10
sc_tp <- 100 / tp_max
axis(1, at = seq(0, tp_max, 20) * sc_tp, labels = seq(0, tp_max, 20),
     pos = y_tp, cex.axis = 0.85, col = AXCOL, tcl = -0.25)
mtext("Total points", side = 2, at = y_tp, las = 1, line = 0.5, cex = 0.95, font = 2)
y_pr <- 0.7
pr_tick <- c(0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
tp_of_p <- function(p) (log(p / (1 - p)) - base_lp) / mx * 100
tp_pr <- tp_of_p(pr_tick)
ok <- tp_pr >= 0 & tp_pr <= tp_max
segments(min(tp_pr[ok]) * sc_tp, y_pr, max(tp_pr[ok]) * sc_tp, y_pr, lwd = 1.4, col = AXCOL)
segments(tp_pr[ok] * sc_tp, y_pr - 0.06, tp_pr[ok] * sc_tp, y_pr + 0.06, lwd = 1.4, col = AXCOL)
text(tp_pr[ok] * sc_tp, y_pr - 0.30, sub("^0\\.", ".", format(pr_tick[ok])), cex = 0.72)
mtext("Predicted probability", side = 2, at = y_pr, las = 1, line = 0.5, cex = 0.95, font = 2)
dev.off()
cat("Nomogram base_lp", round(base_lp, 4), "max range", round(mx, 4),
    "total-points max", tp_max, "\n")

# ================= FIGURE S8 (integer card: predicted vs observed) =================
mp8 <- read.csv(paste0(OUT, "v2_score_risk_mapping.csv"))
ob <- regmatches(mp8$observed_lm24, regexec("([0-9.]+)% \\(n=([0-9]+)\\)", mp8$observed_lm24))
mp8$obs <- sapply(ob, function(x) as.numeric(x[2]))
mp8$n <- sapply(ob, function(x) as.numeric(x[3]))
open_png("FigS8.png", 8.5, 5.6)
par(mar = c(3.6, 4.2, 1.0, 0.8), family = "sans")
plot(NA, xlim = c(-0.4, 15.4), ylim = c(0, 100), axes = FALSE, xlab = "", ylab = "",
     xaxs = "i", yaxs = "i")
abline(h = seq(20, 100, 20), col = GRID, lwd = 0.9)
lines(mp8$score, mp8$predicted_risk_pct, col = "#14548C", lwd = 2.4)
for (i in seq_len(nrow(mp8))) {
  if (!is.na(mp8$obs[i]) && !is.na(mp8$n[i]) && mp8$n[i] > 0) {
    k <- round(mp8$obs[i] * mp8$n[i] / 100)
    ci <- wilson(k, mp8$n[i]) * 100
    segments(mp8$score[i], ci[1], mp8$score[i], ci[2], col = "#333333", lwd = 1.4)
  }
}
points(mp8$score, mp8$obs, pch = 21, bg = "white", col = "#B45A1F", lwd = 2.2, cex = 1.15)
axis(1, at = 0:15, cex.axis = 0.9, col = AXCOL)
axis(2, at = seq(0, 100, 20), las = 1, cex.axis = 0.95, col = AXCOL)
box(bty = "l", col = AXCOL)
mtext("CS-MORT-6 integer score", side = 1, line = 2.3)
mtext("In-hospital mortality (%)", side = 2, line = 2.8)
legend("topleft", inset = c(0.01, 0.02), bty = "n", cex = 0.95,
       lwd = c(2.4, NA), pch = c(NA, 21), col = c("#14548C", "#B45A1F"),
       pt.bg = c(NA, "white"), pt.lwd = 2.2,
       legend = c("Predicted risk (score-to-risk mapping)",
                  "Observed landmark mortality (Wilson 95% CI)"))
dev.off()
cat("FigS8 points:", sum(!is.na(mp8$obs)), "\n")
cat("ALL FIGURES DONE\n")
