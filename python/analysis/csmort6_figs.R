suppressMessages(library(ggplot2)); FIG="outputs/figures"; T="outputs/tables"
# 1. Integer-score calibration (observed mortality per integer score) + logistic fit
g<-read.csv(file.path(T,"integer_calibration_mimic.csv"))
p<-ggplot(g,aes(score,obs))+
  geom_smooth(method="glm",method.args=list(family=binomial),se=TRUE,colour="#1f4e79",fill="#9dc3e6")+
  geom_point(aes(size=n),colour="#1f4e79")+scale_size_area(max_size=6)+
  coord_cartesian(ylim=c(0,1))+labs(title="CS-MORT-6 integer score calibration (MIMIC)",x="Integer score (0-15)",y="Observed in-hospital mortality",size="n")+
  theme_bw(base_size=12)
ggsave(file.path(FIG,"cal_integer_mimic.png"),p,width=5.2,height=5,dpi=300)
# 2. loess calibration (continuous) MIMIC + eICU-AG, from canonical preds
cm<-function(p,y){p<-pmin(pmax(p,1e-6),1-1e-6);lp<-log(p/(1-p));c(slope=unname(coef(glm(y~lp,family=binomial))[2]),citl=unname(coef(glm(y~offset(lp),family=binomial))[1]),brier=mean((p-y)^2))}
cal<-function(df,title,f){m<-cm(df$p,df$y);lab<-sprintf("slope=%.2f CITL=%+.2f Brier=%.3f",m["slope"],m["citl"],m["brier"])
 g<-ggplot(df,aes(p,y))+geom_abline(slope=1,intercept=0,linetype=2,colour="grey50")+geom_smooth(method="loess",se=TRUE,span=.9,colour="#1f4e79",fill="#9dc3e6")+coord_cartesian(xlim=c(0,1),ylim=c(0,1))+labs(title=title,x="Predicted probability",y="Observed mortality (loess)")+annotate("text",x=.03,y=.95,hjust=0,size=3.4,label=lab)+theme_bw(base_size=12)
 ggsave(file.path(FIG,f),g,width=5,height=5,dpi=300)}
m<-read.csv(file.path(T,"dca_mimic_cm6.csv")); cal(m,"MIMIC internal (CV) CS-MORT-6","cal_mimic_internal.png")
ea<-read.csv(file.path(T,"dca_eicu_cm6.csv")); cal(data.frame(p=ea$p_ag,y=ea$y),"eICU external CS-MORT-6-AG (harmonized)","cal_eicu_ag.png")
# 3. DCA mimic + eICU (AG vs BOS,MA2 published + recalibrated)
nb<-function(p,y,t){pos<-p>=t;sum(pos&y==1)/length(y)-(sum(pos&y==0)/length(y))*(t/(1-t))};nba<-function(y,t){pr<-mean(y);pr-(1-pr)*(t/(1-t))}
pts<-seq(.05,.8,.01)
mk<-function(df,all,title,f){gg<-ggplot(df,aes(pt,nb,colour=model))+geom_line(linewidth=.8)+geom_line(data=all,aes(pt,nb),colour="grey40",linetype=2,inherit.aes=FALSE)+geom_hline(yintercept=0,linewidth=.3)+coord_cartesian(ylim=c(-.02,max(df$nb)*1.05))+labs(title=title,x="Threshold probability",y="Net benefit",colour=NULL)+theme_bw(base_size=12)+theme(legend.position=c(.70,.82));ggsave(file.path(FIG,f),gg,width=5.2,height=5,dpi=300)}
dd<-function(pr,y,nm)do.call(rbind,lapply(names(pr),function(k)data.frame(pt=pts,nb=sapply(pts,function(t)nb(pr[[k]],y,t)),model=k)))
mk(dd(list(`CS-MORT-6`=m$p),m$y),data.frame(pt=pts,nb=sapply(pts,function(t)nba(m$y,t))),"DCA: MIMIC internal","dca_mimic.png")
RISK<-c(`0`=.005,`1`=.014,`2`=.039,`3`=.10,`4`=.235,`5`=.46,`6`=.702)
ec<-ea[!is.na(ea$bm),]; ec$pbm<-RISK[as.character(ec$bm)]
lp<-log(pmin(pmax(ec$pbm,1e-6),1-1e-6)/(1-pmin(pmax(ec$pbm,1e-6),1-1e-6))); bmr<-predict(glm(ec$y~lp,family=binomial),type="response")
mk(dd(list(`CS-MORT-6-AG`=ec$p_ag,`BOS,MA2 (published)`=ec$pbm,`BOS,MA2 (recal)`=bmr),ec$y),data.frame(pt=pts,nb=sapply(pts,function(t)nba(ec$y,t))),"DCA: eICU external","dca_eicu.png")
cat("figures: cal_integer_mimic, cal_mimic_internal, cal_eicu_ag, dca_mimic, dca_eicu (all CS-MORT-6)\n")
