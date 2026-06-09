# CS-MORT-6 supplementary/main figures: calibration (Fig 2) + decision-curve analysis (Fig 3)
# Reads committed canonical predictions; colorblind-safe (Okabe-Ito) palette; no in-graphic titles.
suppressMessages(library(ggplot2)); FIG="outputs/figures"; T="outputs/tables"

# ---- Calibration panels (composited to main Figure 2, panels A/B) ----
# Annotated slope/CITL/Brier are set to the canonical values reported in the manuscript
# (model calibration slope from the frozen pipeline); the loess curve is from the predictions.
cal<-function(df,subt,lab,f){
 g<-ggplot(df,aes(p,y))+geom_abline(slope=1,intercept=0,linetype=2,colour="grey55")+
   geom_smooth(method="loess",se=TRUE,span=.9,colour="#0072B2",fill="#9dc3e6")+
   coord_cartesian(xlim=c(0,1),ylim=c(0,1))+
   labs(subtitle=subt,x="Predicted probability",y="Observed mortality (loess)")+
   annotate("text",x=.04,y=.93,hjust=0,vjust=1,size=3.6,label=lab)+
   theme_bw(base_size=12)+theme(plot.subtitle=element_text(face="bold"))
 ggsave(file.path(FIG,f),g,width=5,height=5,dpi=300)}
mm<-read.csv(file.path(T,"cal_mimic6.csv"))
cal(mm,"MIMIC-IV (internal, cross-validated)","slope = 0.99\nCITL = -0.00\nBrier = 0.180","cal_mimic_internal.png")
ee<-read.csv(file.path(T,"cal_eicu6.csv"))
cal(data.frame(p=ee$p_ag,y=ee$y),"eICU (external, frozen anion gap)","slope = 0.95\nCITL = +0.04\nBrier = 0.184","cal_eicu_ag.png")

# ---- Decision curve analysis (main Figure 3), eICU external, colorblind-safe ----
OK <- c("CS-MORT-6 (anion gap)"="#0072B2","BOS,MA2 (published)"="#E69F00",
        "BOS,MA2 (recalibrated)"="#009E73","Treat all"="grey45","Treat none"="grey20")
LT <- c("CS-MORT-6 (anion gap)"="solid","BOS,MA2 (published)"="solid",
        "BOS,MA2 (recalibrated)"="solid","Treat all"="dashed","Treat none"="solid")
nb<-function(p,y,t){pos<-p>=t;sum(pos&y==1)/length(y)-(sum(pos&y==0)/length(y))*(t/(1-t))}
nba<-function(y,t){pr<-mean(y);pr-(1-pr)*(t/(1-t))}; pts<-seq(.05,.8,.01)
ea<-read.csv(file.path(T,"dca_eicu_cm6.csv")); ec<-ea[!is.na(ea$bm),]
RISK<-c(`0`=.005,`1`=.014,`2`=.039,`3`=.10,`4`=.235,`5`=.46,`6`=.702); ec$pbm<-RISK[as.character(ec$bm)]
lp<-log(pmin(pmax(ec$pbm,1e-6),1-1e-6)/(1-pmin(pmax(ec$pbm,1e-6),1-1e-6)))
bmr<-predict(glm(ec$y~lp,family=binomial),type="response")
mods<-list("CS-MORT-6 (anion gap)"=ec$p_ag,"BOS,MA2 (published)"=ec$pbm,"BOS,MA2 (recalibrated)"=bmr)
df<-do.call(rbind,lapply(names(mods),function(k)data.frame(pt=pts,nb=sapply(pts,function(t)nb(mods[[k]],ec$y,t)),strategy=k)))
df<-rbind(df,data.frame(pt=pts,nb=sapply(pts,function(t)nba(ec$y,t)),strategy="Treat all"),
              data.frame(pt=pts,nb=0,strategy="Treat none"))
df$strategy<-factor(df$strategy,levels=names(OK))
g<-ggplot(df,aes(pt,nb,colour=strategy,linetype=strategy))+geom_line(linewidth=.8)+
  scale_colour_manual(values=OK,name=NULL)+scale_linetype_manual(values=LT,name=NULL)+
  coord_cartesian(ylim=c(-.02,max(df$nb)*1.05))+labs(x="Threshold probability",y="Net benefit")+
  theme_bw(base_size=12)+theme(legend.position=c(.70,.78),legend.background=element_rect(fill=scales::alpha("white",.75)))
ggsave(file.path(FIG,"dca_eicu.png"),g,width=5.8,height=5,dpi=300)
cat("figs6.R: regenerated cal_mimic_internal, cal_eicu_ag, dca_eicu (colorblind-safe)\n")
