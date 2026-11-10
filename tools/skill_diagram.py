"""Draws Figure: ACEG Governance Skill workflow (outputs/final/figures/fig_skill_workflow.png)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch

C = {"in": "#2a78d6", "llm": "#eb6834", "tool": "#6250d6", "human": "#1baf7a", "out": "#e34948"}
fig, ax = plt.subplots(figsize=(8.2, 3.0)); ax.set_xlim(0, 100); ax.set_ylim(2, 28); ax.axis("off")
steps = [("in", "1 Blind", ["Advisory or CVE", "mask_severity.py", "strips severity"]),
         ("llm", "2 Code (LLM)", ["codebook.md", "8 domains, 20", "controls; JSON"]),
         ("tool", "3 Score", ["aceg_score.py", "GCS, P(high),", "priority tier"]),
         ("human", "4 Review", ["Confirm D1, D2,", "D3, D7, D8,", "primary domain"]),
         ("out", "5 Remediate", ["playbook.md", "actions, owners,", "checks"])]
w, h, y = 17.5, 13, 13
for i, (k, t, lines) in enumerate(steps):
    x = 1 + i * 20
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1", fc="white", ec=C[k], lw=2))
    ax.add_patch(FancyBboxPatch((x, y + h - 4.5), w, 4.5, boxstyle="round,pad=0.3,rounding_size=1", fc=C[k], ec=C[k], lw=2))
    ax.text(x + w / 2, y + h - 2.25, t, ha="center", va="center", color="white", fontsize=9.5, fontweight="bold", family="DejaVu Sans")
    ax.text(x + 0.8, y + h - 6.3, "\n".join(lines), ha="left", va="top", fontsize=8.2, family="DejaVu Sans", linespacing=1.4)
    if i < 4:
        ax.add_patch(FancyArrowPatch((x + w + 0.4, y + h / 2), (x + 20 - 0.4, y + h / 2), arrowstyle="-|>", mutation_scale=13, lw=1.5, color="#52514e"))
ax.text(50, 8.5, "Modes: single advisory -> JSON + HTML scorecard   |   portfolio CSV -> scored CSV and P1/P2/P3 counts   |   REST API (src/10_scorecard_service.py)",
        ha="center", fontsize=7.4, family="DejaVu Sans", color="#52514e")
leg = [Patch(fc=C["in"], label="Input"), Patch(fc=C["llm"], label="LLM step"), Patch(fc=C["tool"], label="Deterministic script"),
       Patch(fc=C["human"], label="Human-in-the-loop"), Patch(fc=C["out"], label="Output")]
ax.legend(handles=leg, loc="lower center", ncol=5, fontsize=7.6, frameon=False, bbox_to_anchor=(0.5, -0.04))
fig.tight_layout(); fig.savefig("/home/claude/work/repo/outputs/final/figures/fig_skill_workflow.png", dpi=220, facecolor="white")
