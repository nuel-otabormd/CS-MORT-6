suppressMessages({library(ggplot2)})
FIG <- "outputs/figures"
calmetrics <- function(p,y){
  p <- pmin(pmax(p,1e-6),1-1e-6); lp <- log(p/(1-p))
  fit <- glm(y~lp, family=binomial)
  slope <- coef(fit)[2]
  citl  <- coef(glm(y~offset(lp), family=binomial))[1]   # calibration-in-the-large
  brier <- mean((p-y)^2)
  c(slope=unname(slope), citl=unname(citl), brier=brier, n=length(y), obs=mean(y), pred=mean(p))
}
calplot <- function(df, title, fname){
  m <- calmetrics(df$p, df$y)
  lab <- sprintf("n=%d  obs=%.3f  pred=%.3f\nslope=%.2f  CITL=%+.2f  Brier=%.3f",
                 m["n"], m["obs"], m["pred"], m["slope"], m["citl"], m["brier"])
  g <- ggplot(df, aes(p,y)) +
    geom_abline(slope=1,intercept=0,linetype=2,colour="grey50") +
    geom_smooth(method="loess", se=TRUE, span=0.9, colour="#1f4e79", fill="#9dc3e6") +
    geom_rug(data=subset(df,y==1), sides="t", alpha=0.15) +
    geom_rug(data=subset(df,y==0), sides="b", alpha=0.15) +
    coord_cartesian(xlim=c(0,1), ylim=c(0,1)) +
    labs(title=title, x="Predicted probability", y="Observed mortality (loess)") +
    annotate("text", x=0.02, y=0.95, hjust=0, vjust=1, size=3.2, label=lab) +
    theme_bw(base_size=12)
  ggsave(file.path(FIG,fname), g, width=5, height=5, dpi=300)
  cat(sprintf("  %-28s slope=%.2f CITL=%+.2f Brier=%.3f -> %s\n", title, m["slope"],m["citl"],m["brier"], fname))
}
cat("CALIBRATION (loess):\n")
mim <- read.csv("/tmp/cal_mimic.csv"); calplot(mim, "MIMIC internal (CV) CS-MORT-7", "cal_mimic_internal.png")
eic <- read.csv("/tmp/cal_eicu.csv")
calplot(data.frame(p=eic$p_ag, y=eic$y), "eICU external CS-MORT-7-AG", "cal_eicu_ag.png")
calplot(data.frame(p=eic$p_lac,y=eic$y), "eICU external CS-MORT-7 (lactate)", "cal_eicu_lac.png")

## ---- DECISION CURVE ANALYSIS (manual net benefit) ----
nb <- function(p,y,pt){ pos <- p>=pt; tp<-sum(pos&y==1); fp<-sum(pos&y==0); n<-length(y)
  tp/n - (fp/n)*(pt/(1-pt)) }
nb_all <- function(y,pt){ prev<-mean(y); prev - (1-prev)*(pt/(1-pt)) }
dca_df <- function(preds, y, name){
  pts <- seq(0.05,0.80,by=0.01)
  do.call(rbind, lapply(names(preds), function(k)
    data.frame(pt=pts, nb=sapply(pts, function(t) nb(preds[[k]],y,t)), model=k, cohort=name)))
}
mk_dca <- function(df, allrow, title, fname){
  g <- ggplot(df, aes(pt,nb,colour=model)) +
    geom_line(linewidth=0.8) +
    geom_line(data=allrow, aes(pt,nb), colour="grey40", linetype=2, inherit.aes=FALSE) +
    geom_hline(yintercept=0, colour="black", linewidth=0.3) +
    coord_cartesian(ylim=c(-0.02, max(df$nb)*1.05)) +
    labs(title=title, x="Threshold probability", y="Net benefit", colour=NULL) +
    theme_bw(base_size=12) + theme(legend.position=c(0.70,0.82))
  ggsave(file.path(FIG,fname), g, width=5.2, height=5, dpi=300); cat("  ->",fname,"\n")
}
cat("DECISION CURVES:\n")
pts <- seq(0.05,0.80,by=0.01)
# MIMIC internal
mdf <- dca_df(list(`CS-MORT-7`=mim$p), mim$y, "MIMIC")
mall<- data.frame(pt=pts, nb=sapply(pts,function(t) nb_all(mim$y,t)))
mk_dca(mdf, mall, "DCA: MIMIC internal", "dca_mimic.png")
# eICU external: AG vs BOS,MA2 (as-published AND recalibrated, for fairness) on common scorable set
ec <- eic[!is.na(eic$p_bm),]
lp <- log(pmin(pmax(ec$p_bm,1e-6),1-1e-6)/(1-pmin(pmax(ec$p_bm,1e-6),1-1e-6)))
bm_rc <- predict(glm(ec$y~lp, family=binomial), type="response")   # eICU-recalibrated BOS,MA2
edf <- dca_df(list(`CS-MORT-7-AG`=ec$p_ag, `BOS,MA2 (published)`=ec$p_bm, `BOS,MA2 (recalibrated)`=bm_rc), ec$y, "eICU")
eall<- data.frame(pt=pts, nb=sapply(pts,function(t) nb_all(ec$y,t)))
mk_dca(edf, eall, "DCA: eICU external (common scorable n=1127)", "dca_eicu.png")
cat("DONE\n")
