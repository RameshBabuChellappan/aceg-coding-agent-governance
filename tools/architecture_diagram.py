"""Draws Figure: end-to-end ACEG workflow (outputs/final/figures/fig_architecture.png)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch
from matplotlib.lines import Line2D

C = {"data": "#2a78d6", "prep": "#1baf7a", "code": "#eb6834", "model": "#6250d6", "deploy": "#e34948"}
fig, ax = plt.subplots(figsize=(10, 5.4))
ax.set_xlim(0, 100); ax.set_ylim(3, 55); ax.axis("off")

def box(x, y, w, h, title, lines, kind, num):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                fc="white", ec=C[kind], lw=2))
    ax.add_patch(FancyBboxPatch((x, y + h - 4.2), w, 4.2, boxstyle="round,pad=0.4,rounding_size=1.2",
                                fc=C[kind], ec=C[kind], lw=2))
    ax.text(x + w / 2, y + h - 2.1, f"{num}  {title}", ha="center", va="center", color="white",
            fontsize=9.2, fontweight="bold", family="DejaVu Sans")
    ax.text(x + 1.0, y + h - 5.6, "\n".join(lines), ha="left", va="top", fontsize=7.3,
            family="DejaVu Sans", color="#0b0b0b", linespacing=1.35)

def arrow(p, q, style="-", color="#52514e", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=13, lw=1.5, color=color,
                                 linestyle=style, connectionstyle=f"arc3,rad={rad}"))

W, H = 22, 15.5
top, bot = 37, 9
box(1, top, W, H, "Data", ["GitHub Advisory Database", "CVE List V5 (git clones)", "Frozen 11 Oct 2026", "239 candidate records", "Eligibility screening", "-> N = 223 cases"], "data", "1")
box(26, top, W, H, "Preprocessing", ["Merge on CVE identifier", "Missing values: recover / flag", "Outliers: Tukey fences, kept", "Encoding: binary, one-hot,", "  standardized GCS (z)", "Severity text masked for coders"], "prep", "2")
box(51, top, W, H, "EDA", ["Disclosures by quarter", "CVSS distribution, 70:30 split", "Cases by product (clusters)", "Chi-square screens of", "  covariates vs. high impact", "Decisions -> metrics, covariates"], "prep", "3")
box(76, top, W, H, "Feature Engineering", ["Coder 1, Coder 2 (blind)", "LLM coder (Claude, blind)", "2-of-3 majority labels", "8 domains, 20 control breaches", "GCS, n_domains, CWE group", "SQLite: data/aceg.db"], "code", "4")
box(76, bot, W, H, "Model", ["RQ1 Wilson CI, binomial test", "RQ2 chi-square, Cramer's V", "RQ3 logistic regression (H3)", "M0-M7: logit, RF, GBM, MLP", "RQ4 Cohen's / Fleiss' kappa", "75/25 split + 5-fold CV"], "model", "5")
box(51, bot, W, H, "Evaluation", ["Train vs. test AUC, F1,", "  balanced accuracy, Brier", "Repeated CV (10 x 5)", "Bootstrap 95% CIs", "Sensitivity analyses", "Best model: M7 (RF)"], "model", "6")
box(26, bot, W, H, "Deployment", ["ACEG Governance Skill (agent", "  skill: code, score, remediate)", "Scorecard REST API (Flask)", "HTML governance scorecard", "Model artefacts (pickle, JSON)", "ACEG Version 2 codebook"], "deploy", "7")
box(1, bot, W, H, "Users", ["Platform / DevSecOps teams", "AI governance office", "CISO and risk committees", "Agent vendors", "Inputs: new advisory", "Outputs: priority + controls"], "data", "8")
y1 = top + H / 2
for x0 in (23.6, 48.6, 73.6):
    arrow((x0, y1), (x0 + 2.2, y1))
arrow((87, top - 0.6), (87, bot + H + 0.6))
y2 = bot + H / 2
for x0 in (75.4, 50.4, 25.4):
    arrow((x0, y2), (x0 - 2.2, y2))
arrow((37, bot + H + 0.6), (80, top - 0.6), style="--", color=C["code"], rad=-0.15)
ax.text(66, 27.0, "feedback: low-kappa domains and uncovered cases -> ACEG Version 2", fontsize=7.5,
        color=C["code"], ha="center", style="italic", family="DejaVu Sans")
leg = [Patch(fc=C["data"], label="Data sources and users"), Patch(fc=C["prep"], label="Processing and EDA"),
       Patch(fc=C["code"], label="Human and LLM coding"), Patch(fc=C["model"], label="Modelling and evaluation"),
       Patch(fc=C["deploy"], label="Deployment"),
       Line2D([0], [0], color="#52514e", lw=1.5, label="Data flow"),
       Line2D([0], [0], color=C["code"], lw=1.5, ls="--", label="Feedback loop")]
ax.legend(handles=leg, loc="lower center", ncol=4, fontsize=7.6, frameon=False, bbox_to_anchor=(0.5, -0.06))
fig.tight_layout()
fig.savefig("/home/claude/work/repo/outputs/final/figures/fig_architecture.png", dpi=220, facecolor="white")
