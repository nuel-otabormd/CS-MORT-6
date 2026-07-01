# Shared publication theme for CS-MORT-6 figures.
# Colorblind-safe (Okabe-Ito) palettes; Arial/Helvetica; designed for 300+ DPI print.
suppressMessages({library(ggplot2); library(dplyr); library(tidyr); library(scales); library(patchwork)})

OI <- c(blue="#0072B2", vermill="#D55E00", green="#009E73", orange="#E69F00",
        sky="#56B4E9", yellow="#F0E442", pink="#CC79A7", grey="#666666", black="#000000")
SEQ3 <- c(Low="#9ECAE1", Mid="#4292C6", High="#08519C")          # sequential Blues (severity)
TRAJ <- c(Improved="#009E73", Stable="#999999", Worsened="#D55E00")

theme_pub <- function(base=9){
  theme_classic(base_size=base, base_family="Helvetica") +
  theme(
    axis.title=element_text(face="bold", size=base),
    axis.text=element_text(colour="black", size=base-0.5),
    axis.line=element_line(linewidth=0.4, colour="black"),
    axis.ticks=element_line(linewidth=0.4, colour="black"),
    plot.title=element_text(face="bold", size=base+1, hjust=0),
    plot.subtitle=element_text(size=base-0.5, colour="#333333"),
    legend.key.size=unit(3.4,"mm"),
    legend.title=element_text(face="bold", size=base-0.5),
    legend.text=element_text(size=base-1),
    strip.background=element_rect(fill="#F0F0F0", colour=NA),
    strip.text=element_text(face="bold", size=base),
    plot.tag=element_text(face="bold", size=base+3),
    panel.spacing=unit(4,"mm")
  )
}
wilson <- function(x,n,z=1.96){ p<-x/n; d<-1+z^2/n
  lo<-(p+z^2/(2*n)-z*sqrt(p*(1-p)/n+z^2/(4*n^2)))/d
  hi<-(p+z^2/(2*n)+z*sqrt(p*(1-p)/n+z^2/(4*n^2)))/d
  data.frame(lo=lo*100, hi=hi*100) }
save_fig <- function(p, stem, w, h){
  ggsave(paste0(stem,".tiff"), p, width=w, height=h, units="in", dpi=300, compression="lzw", device="tiff")
  ggsave(paste0(stem,".pdf"),  p, width=w, height=h, units="in", device="pdf")
  ggsave(paste0(stem,".png"),  p, width=w, height=h, units="in", dpi=300)
  cat("saved", stem, "\n")
}
