suppressMessages({library(ggplot2)})
FIG="outputs/figures"
theme_pub <- theme_bw(base_size=11, base_family="Helvetica") +
  theme(panel.grid.minor=element_blank(),
        plot.title=element_text(face="bold", size=12),
        strip.background=element_rect(fill="grey92"),
        strip.text=element_text(face="bold"),
        legend.position="top")
# colorblind-safe (Okabe-Ito subset)
pal3 <- c("Low"="#9ECAE1","Mid"="#4292C6","High"="#08519C")  # ColorBrewer Blues, sequential, colorblind-safe

## ---- Figure 4: Within-SCAI-stage resolution (MIMIC + eICU) ----
w <- read.csv(file.path(FIG,"../tables/fig4_withinstage.csv"))
w$tertile <- factor(w$tertile, levels=c("Low","Mid","High"))
w$cohort  <- factor(w$cohort, levels=c("MIMIC","eICU"))
g4 <- ggplot(w, aes(x=stage, y=mortality, fill=tertile)) +
  geom_col(position=position_dodge(0.8), width=0.75, colour="grey20", linewidth=0.2) +
  geom_text(aes(label=sprintf("%.0f", mortality)), position=position_dodge(0.8), vjust=-0.3, size=2.6) +
  facet_wrap(~cohort) +
  scale_fill_manual(values=pal3, name="CS-MORT-6 tertile") +
  scale_y_continuous(limits=c(0,95), expand=expansion(mult=c(0,0.05))) +
  labs(x="SCAI shock stage", y="In-hospital mortality (%)") +
  theme_pub
ggsave(file.path(FIG,"Figure2_within_scai_stage.tiff"), g4, width=7, height=4.2, dpi=600, compression="lzw")
ggsave(file.path(FIG,"Figure2_within_scai_stage.pdf"), g4, width=7, height=4.2)
ggsave(file.path(FIG,"Figure2_within_scai_stage.png"), g4, width=7, height=4.2, dpi=600)

## ---- Figure 5: Score trajectory and deterioration ----
tr <- read.csv(file.path(FIG,"../tables/fig5_trajectory.csv"))
tr$panel <- ifelse(grepl("mid-range", tr$trajectory), "Within identical 24h score (4-7)", "All 48-hour survivors")
tr$trajectory <- gsub(" \\(mid-range 24h\\)","",tr$trajectory)
tr$trajectory <- factor(tr$trajectory, levels=c("Improved","Stable","Worsened"))
tr$panel <- factor(tr$panel, levels=c("All 48-hour survivors","Within identical 24h score (4-7)"))
palT <- c("Improved"="#0072B2","Stable"="#999999","Worsened"="#D55E00")  # blue/grey/vermillion, colorblind-safe
g5 <- ggplot(tr, aes(x=trajectory, y=mortality, fill=trajectory)) +
  geom_col(width=0.65, colour="grey20", linewidth=0.2) +
  geom_text(aes(label=sprintf("%.1f%%\n(n=%d)", mortality, n)), vjust=-0.2, size=2.6, lineheight=0.9) +
  facet_wrap(~panel) +
  scale_fill_manual(values=palT, guide="none") +
  scale_y_continuous(limits=c(0,72), expand=expansion(mult=c(0,0.08))) +
  labs(x="Change in CS-MORT-6 score, 24 to 48 hours", y="In-hospital mortality (%)") +
  theme_pub
ggsave(file.path(FIG,"Figure3_trajectory.tiff"), g5, width=7, height=4.0, dpi=600, compression="lzw")
ggsave(file.path(FIG,"Figure3_trajectory.pdf"), g5, width=7, height=4.0)
ggsave(file.path(FIG,"Figure3_trajectory.png"), g5, width=7, height=4.0, dpi=600)
cat("Figures 4 and 5 saved (PNG + TIFF, 600 DPI)\n")
