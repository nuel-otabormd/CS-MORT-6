suppressMessages(library(ggplot2))
FIG="outputs/figures"
box <- function(x,y,w,h,label,fill="white") data.frame(x=x,y=y,w=w,h=h,label=label,fill=fill)
B <- rbind(
 box(2.0,9.0,3.4,1.1,"Adult ICU admissions with documented\ncardiogenic shock (ICD code or affirmed\ndischarge-note mention)\nn = 4,315"),
 box(2.0,6.5,3.4,0.9,"Documented cardiogenic shock with\n1 or more objective criteria\nn = 4,089"),
 box(2.0,4.0,3.4,0.9,"MIMIC-IV derivation cohort\nn = 3,103","#EAF2FB"),
 box(6.4,9.0,3.2,1.1,"eICU admissions with cardiogenic\nshock (APACHE diagnosis string)\nn = 1,866"),
 box(6.4,4.0,3.2,0.9,"eICU external validation cohort\nn = 1,866","#EAF2FB"))
E <- rbind(
 box(4.2,7.7,3.0,0.8,"Excluded: no objective shock\ncriterion within 24 h (n = 226)","#F7F7F7"),
 box(4.2,5.2,3.0,0.8,"Excluded: non-index ICU stay,\none per patient (n = 986)","#F7F7F7"))
arr <- data.frame(x=c(2.0,2.0,6.4),xe=c(2.0,2.0,6.4),y=c(8.45,5.95,8.45),ye=c(6.95,4.45,4.45))
side <- data.frame(x=c(2.0,2.0),xe=c(2.7,2.7),y=c(7.7,5.2),ye=c(7.7,5.2))
g <- ggplot() +
 geom_tile(data=B, aes(x,y,width=w,height=h,fill=fill), colour="grey25", linewidth=0.4) +
 geom_tile(data=E, aes(x,y,width=w,height=h), fill="#F7F7F7", colour="grey55", linewidth=0.3) +
 geom_text(data=B, aes(x,y,label=label), size=2.7, family="Helvetica", lineheight=0.92) +
 geom_text(data=E, aes(x,y,label=label), size=2.5, family="Helvetica", lineheight=0.92) +
 geom_segment(data=arr, aes(x=x,xend=xe,y=y,yend=ye), arrow=arrow(length=unit(0.16,"cm"),type="closed"), linewidth=0.4) +
 geom_segment(data=side, aes(x=x,xend=xe,y=y,yend=ye), linewidth=0.4) +
 scale_fill_identity() +
 annotate("text", x=2.0, y=9.9, label="MIMIC-IV (Development)", fontface="bold", size=3.2, family="Helvetica") +
 annotate("text", x=6.4, y=9.9, label="eICU (External Validation)", fontface="bold", size=3.2, family="Helvetica") +
 coord_cartesian(xlim=c(0.2,8.1), ylim=c(3.3,10.2)) + theme_void()
ggsave(file.path(FIG,"Figure1_consort.tiff"), g, width=7, height=5, dpi=600, compression="lzw")
ggsave(file.path(FIG,"Figure1_consort.pdf"), g, width=7, height=5)
ggsave(file.path(FIG,"Figure1_consort.png"), g, width=7, height=5, dpi=600)
cat("Figure 1 CONSORT saved\n")
