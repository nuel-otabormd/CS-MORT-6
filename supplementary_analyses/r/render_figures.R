# CS-MORT-6 — render main and supplementary figures at 300 DPI.
# Run from review/figures/scripts/
args <- commandArgs(trailingOnly=FALSE)
here <- dirname(sub("--file=","",args[grep("--file=",args)]))
if(length(here)==0) here <- getwd()
source(file.path(here,"theme_csmort.R"))
BASE <- normalizePath(file.path(here, ".."))   # supplementary_analyses/ root
FD  <- file.path(BASE, "data")     # exported input CSVs (see sql/exports.sql)
OUT <- file.path(BASE, "out")      # CSVs produced by python/02_ and 03_
RND <- file.path(BASE, "figures"); dir.create(RND,showWarnings=FALSE,recursive=TRUE)
setwd(RND)

## ---- helpers: calibration curve + net benefit ----
cal_df <- function(p,y,bins=10){
  d <- data.frame(p=p,y=y) |> filter(!is.na(p))
  lo <- loess(y~p, data=d, span=0.75, degree=1)
  gx <- seq(quantile(d$p,.02), quantile(d$p,.98), length=100)
  pr <- predict(lo, gx, se=TRUE)
  curve <- data.frame(p=gx, fit=pmax(0,pmin(1,pr$fit)),
                      lo=pmax(0,pr$fit-1.96*pr$se.fit), hi=pmin(1,pr$fit+1.96*pr$se.fit))
  d$bin <- cut(d$p, quantile(d$p, seq(0,1,length=bins+1)), include.lowest=TRUE)
  pts <- d |> group_by(bin) |> summarise(px=mean(p), py=mean(y), n=n(), .groups="drop")
  list(curve=curve, pts=pts)
}
brier <- function(p,y) mean((p-y)^2, na.rm=TRUE)

## ============================================================
## FIGURE 2 — Calibration (A MIMIC internal, B eICU external AG)
## ============================================================
cm <- read.csv(file.path(FD,"cal_mimic6.csv")); ce <- read.csv(file.path(FD,"cal_eicu6.csv"))
mk_cal <- function(p,y,slope,citl,tag,title){
  cc <- cal_df(p,y)
  ann <- sprintf("Slope %.2f\nCITL %+.2f\nBrier %.3f", slope, citl, brier(p,y))
  ggplot() +
    geom_abline(slope=1,intercept=0,linetype=2,colour=OI["grey"],linewidth=0.4) +
    geom_ribbon(data=cc$curve,aes(p,ymin=lo,ymax=hi),fill=OI["blue"],alpha=0.15) +
    geom_line(data=cc$curve,aes(p,fit),colour=OI["blue"],linewidth=0.9) +
    geom_point(data=cc$pts,aes(px,py,size=n),colour=OI["black"],fill="white",shape=21,stroke=0.4) +
    scale_size_area(max_size=3.2,guide="none") +
    annotate("text",x=0.02,y=0.96,label=ann,hjust=0,vjust=1,size=2.7,family="Helvetica") +
    scale_x_continuous("Predicted probability",limits=c(0,1),labels=percent_format(1),expand=c(0,0)) +
    scale_y_continuous("Observed mortality",limits=c(0,1),labels=percent_format(1),expand=c(0,0)) +
    coord_equal() + labs(tag=tag,title=title) + theme_pub()
}
A <- mk_cal(cm$p, cm$y, 0.99, -0.001, "A", "MIMIC-IV (internal, cross-validated)")
B <- mk_cal(ce$p_ag, ce$y, 0.95, 0.044, "B", "eICU (external, anion-gap model)")
save_fig(A|B, "Figure2_Calibration", 7.0, 3.7)

## ============================================================
## FIGURE 3 — Decision Curve Analysis (eICU commonly scorable)
## ============================================================
dca <- read.csv(file.path(FD,"dca_eicu_cm6.csv"))
bm_risk <- c(`0`=.005,`1`=.014,`2`=.039,`3`=.10,`4`=.235,`5`=.46,`6`=.702)
dca$bm_p <- bm_risk[as.character(dca$bm)]
# recalibrate BOS,MA2 to eICU base rate via logistic recalibration on its own linear predictor
cc <- dca[!is.na(dca$bm_p),]
lp <- log(cc$bm_p/(1-cc$bm_p)); fit <- glm(cc$y~lp, family=binomial)
cc$bm_recal <- predict(fit, type="response")
nb <- function(p,y,th) mean((p>=th)*y,na.rm=TRUE) - mean((p>=th)*(1-y),na.rm=TRUE)*(th/(1-th))
ths <- seq(0.05,0.7,0.01); base <- mean(cc$y)
mk <- function(pv,lab) data.frame(th=ths, nb=sapply(ths, function(t) nb(pv,cc$y,t)), model=lab)
NB <- bind_rows(
  mk(cc$p_ag, "CS-MORT-6 (anion gap)"),
  mk(cc$bm_recal, "BOS,MA2 (recalibrated)"),
  mk(cc$bm_p, "BOS,MA2 (published)"),
  data.frame(th=ths, nb=sapply(ths,function(t) base - (1-base)*(t/(1-t))), model="Treat all"),
  data.frame(th=ths, nb=0, model="Treat none"))
NB$model <- factor(NB$model, levels=c("CS-MORT-6 (anion gap)","BOS,MA2 (recalibrated)","BOS,MA2 (published)","Treat all","Treat none"))
cols <- c("CS-MORT-6 (anion gap)"=OI[["blue"]],"BOS,MA2 (recalibrated)"=OI[["green"]],
          "BOS,MA2 (published)"=OI[["vermill"]],"Treat all"=OI[["grey"]],"Treat none"="#BBBBBB")
lty <- c("CS-MORT-6 (anion gap)"=1,"BOS,MA2 (recalibrated)"=1,"BOS,MA2 (published)"=1,"Treat all"=2,"Treat none"=3)
f3 <- ggplot(NB,aes(th,nb,colour=model,linetype=model))+geom_line(linewidth=0.9)+
  scale_colour_manual(values=cols,name=NULL)+scale_linetype_manual(values=lty,name=NULL)+
  scale_x_continuous("Threshold probability",labels=percent_format(1),expand=c(0,0))+
  scale_y_continuous("Net benefit",limits=c(-0.02,max(NB$nb)*1.05),expand=c(0,0))+
  coord_cartesian(clip="off")+theme_pub()+theme(legend.position=c(0.98,0.98),legend.justification=c(1,1),
    legend.background=element_rect(fill=alpha("white",0.7),colour=NA))
save_fig(f3, "Figure3_DecisionCurve", 5.0, 3.8)

## ============================================================
## FIGURE 4 — Within-SCAI-stage tertiles (MIMIC + eICU), CS-MORT-6
## ============================================================
w <- read.csv(file.path(FD,"fig4_withinstage.csv"))
w$tertile <- factor(w$tertile, levels=c("Low","Mid","High"))
w$cohort  <- factor(w$cohort, levels=c("MIMIC","eICU"), labels=c("MIMIC-IV (derivation)","eICU (validation)"))
ci <- wilson(round(w$mortality/100*w$n), w$n); w$lo<-ci$lo; w$hi<-ci$hi
mk_within <- function(df, title=NULL){
  ggplot(df,aes(stage,mortality,fill=tertile))+
    geom_col(position=position_dodge(0.8),width=0.72,colour="white",linewidth=0.2)+
    geom_errorbar(aes(ymin=lo,ymax=hi),position=position_dodge(0.8),width=0.22,linewidth=0.35,colour="#333333")+
    geom_text(aes(label=n,y=2),position=position_dodge(0.8),vjust=0,size=1.9,colour="white")+
    facet_wrap(~cohort)+scale_fill_manual(values=SEQ3,name="CS-MORT-6\ntertile")+
    scale_y_continuous("In-hospital mortality",labels=percent_format(scale=1),limits=c(0,100),expand=c(0,0))+
    scale_x_discrete("SCAI shock stage")+labs(title=title)+theme_pub()
}
save_fig(mk_within(w), "Figure4_WithinSCAIStage", 7.0, 3.6)

## ============================================================
## FIGURE 5 — Serial trajectory (all survivors + mid-range 4-7)
## ============================================================
tr <- read.csv(file.path(FD,"fig5_trajectory.csv"))
tr$panel <- ifelse(grepl("mid-range",tr$trajectory),"Same intermediate 24-h score (4-7)","All 48-h survivors")
tr$trajectory <- factor(gsub(" \\(mid-range 24h\\)","",tr$trajectory), levels=c("Improved","Stable","Worsened"))
tr$panel <- factor(tr$panel, levels=c("All 48-h survivors","Same intermediate 24-h score (4-7)"))
ci <- wilson(round(tr$mortality/100*tr$n), tr$n); tr$lo<-ci$lo; tr$hi<-ci$hi
f5 <- ggplot(tr,aes(trajectory,mortality,fill=trajectory))+
  geom_col(width=0.66,colour="white",linewidth=0.2)+
  geom_errorbar(aes(ymin=lo,ymax=hi),width=0.2,linewidth=0.35,colour="#333333")+
  geom_text(aes(label=sprintf("%.1f%%",mortality)),vjust=-0.5,size=2.5,fontface="bold")+
  geom_text(aes(label=paste0("n=",n),y=2),vjust=0,size=1.9,colour="white")+
  facet_wrap(~panel)+scale_fill_manual(values=TRAJ,guide="none")+
  scale_y_continuous("In-hospital mortality",labels=percent_format(scale=1),limits=c(0,70),expand=c(0,0))+
  scale_x_discrete("24-to-48-hour CS-MORT-6 change")+theme_pub()
save_fig(f5, "Figure5_Trajectory", 6.4, 3.6)

## ============================================================
## NEW SUPPL FIGURE S1 — OHCA-free (CS-MORT-5) within-stage tertiles
## Within-stage resolution using the OHCA-free score (sensitivity)
## ============================================================
s <- read.csv(file.path(OUT,"fig_s_ohca_free_withinstage.csv"))
s$tertile <- factor(s$tertile, levels=c("Low","Mid","High"))
s$cohort  <- factor(s$cohort, levels=c("MIMIC","eICU"), labels=c("MIMIC-IV (derivation)","eICU (validation)"))
fs1 <- ggplot(s,aes(stage,mortality,fill=tertile))+
  geom_col(position=position_dodge(0.8),width=0.72,colour="white",linewidth=0.2)+
  geom_errorbar(aes(ymin=lo,ymax=hi),position=position_dodge(0.8),width=0.22,linewidth=0.35,colour="#333333")+
  geom_text(aes(label=n,y=2),position=position_dodge(0.8),vjust=0,size=1.9,colour="white")+
  facet_wrap(~cohort)+scale_fill_manual(values=SEQ3,name="CS-MORT-5\ntertile\n(OHCA-free)")+
  scale_y_continuous("In-hospital mortality",labels=percent_format(scale=1),limits=c(0,100),expand=c(0,0))+
  scale_x_discrete("SCAI shock stage")+theme_pub()
save_fig(fs1, "FigureS1_WithinStage_OHCAfree", 7.0, 3.6)

## ============================================================
## NEW SUPPL FIGURE S2 — Subgroup discrimination + calibration (fairness)
## Subgroup discrimination and calibration
## ============================================================
fr <- read.csv(file.path(OUT,"fairness_subgroups.csv"))
fr$subgroup <- factor(fr$subgroup, levels=rev(c("M","F","White","Black","Other/Unknown")),
                      labels=rev(c("Male","Female","White","Black","Other/Unknown")))
pa <- ggplot(fr,aes(auroc,subgroup))+
  geom_vline(xintercept=0.5,linetype=3,colour=OI["grey"])+
  geom_errorbarh(aes(xmin=auroc_lo,xmax=auroc_hi),height=0.22,linewidth=0.4)+
  geom_point(aes(size=deaths),colour=OI["blue"])+scale_size_area(max_size=4,name="Deaths")+
  scale_x_continuous("Subgroup AUROC (95% CI)",limits=c(0.5,0.95))+ylab(NULL)+
  labs(tag="A",title="Discrimination")+theme_pub()
pb <- ggplot(fr,aes(citl,subgroup))+
  geom_vline(xintercept=0,linetype=2,colour=OI["grey"])+
  geom_segment(aes(x=0,xend=citl,yend=subgroup),colour="#BBBBBB",linewidth=0.5)+
  geom_point(aes(colour=abs(citl)>0.2),size=2.6)+
  scale_colour_manual(values=c(`FALSE`=OI[["green"]],`TRUE`=OI[["vermill"]]),guide="none")+
  scale_x_continuous("Calibration-in-the-large",limits=c(-0.45,0.45))+ylab(NULL)+
  labs(tag="B",title="Calibration")+theme_pub()
save_fig(pa|pb, "FigureS2_Fairness_Subgroups", 7.0, 2.9)

cat("\nAll figures rendered to", RND, "\n")

## ============================================================
## NEW SUPPL FIGURE S3 — Non-staging-variables-only within-stage
## (age, urine output, BUN, RDW; published weights; lactate & OHCA excluded)
## Within-stage using only non-staging variables (sensitivity)
## ============================================================
s3 <- read.csv(file.path(OUT,"fig_s3_nonstaging_withinstage.csv"))
s3$tertile <- factor(s3$tertile, levels=c("Low","Mid","High"))
s3$cohort  <- factor(s3$cohort, levels=c("MIMIC-IV","eICU"),
                     labels=c("MIMIC-IV (derivation)","eICU (validation)"))
fs3 <- ggplot(s3,aes(stage,mortality,fill=tertile))+
  geom_col(position=position_dodge(0.8),width=0.72,colour="white",linewidth=0.2)+
  geom_errorbar(aes(ymin=lo,ymax=hi),position=position_dodge(0.8),width=0.22,linewidth=0.35,colour="#333333")+
  geom_text(aes(label=n,y=2),position=position_dodge(0.8),vjust=0,size=1.9,colour="white")+
  facet_wrap(~cohort)+scale_fill_manual(values=SEQ3,name="Non-staging\nsub-score\ntertile")+
  scale_y_continuous("In-hospital mortality",labels=percent_format(scale=1),limits=c(0,100),expand=c(0,0))+
  scale_x_discrete("SCAI shock stage")+theme_pub()
save_fig(fs3, "FigureS3_WithinStage_NonStaging", 7.0, 3.6)
