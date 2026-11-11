"""Step 9 - final analysis for RQ1-RQ4, predictive models, and all report tables and figures.

Reads the analysis view from the project SQLite database (data/aceg.db) and writes
tables to outputs/final/tables/, figures to outputs/final/figures/ and a summary to
outputs/final/summary.json. Seed 42 throughout. Run: python src/09_final_analysis.py
"""
import json
import pickle
import sqlite3
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import (GridSearchCV, RepeatedStratifiedKFold, StratifiedKFold,
                                     cross_val_predict, train_test_split)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from aceg_common import ROOT, DOM, CTRL, LINK, FAMILY, FAMILY_NAME, DOM_NAME, derive
from stats_utils import (wilson, logit_fit, hosmer_lemeshow, vif, kappa, boot_ci, fleiss,
                         binclass)

warnings.filterwarnings("ignore")
SEED = 42
OUT = ROOT / "outputs/final"
TAB, FIG = OUT / "tables", OUT / "figures"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
S = {}  # summary

# ---------- plotting style (light, print) ----------
BLUE, ORANGE, AQUA, YELLOW, MAG, GREEN, VIOLET, RED = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                                                       "#e87ba4", "#008300", "#6250d6", "#e34948")
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "legend.frameon": False, "figure.dpi": 100})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.png", dpi=220, facecolor="white")
    plt.close(fig)


# ---------- data access through the database ----------
con = sqlite3.connect(ROOT / "data/aceg.db")
df = pd.read_sql("SELECT * FROM v_analysis ORDER BY case_id", con)
codes = {k: pd.read_sql(f"SELECT * FROM codes_{k} ORDER BY case_id", con)
         for k in ("coder1", "coder2", "llm", "gold")}
con.close()
N = len(df)
df["ecosystem"] = (df.component_type == "ecosystem").astype(int)
df["year_2026"] = (df.year == 2026).astype(int)
df["cvss_v4"] = df.cvss_vector.fillna("").str.startswith("CVSS:4").astype(int) if "cvss_vector" in df else 0
src = pd.read_csv(ROOT / "data/processed/cases_to_code.csv").set_index("case_id").loc[df.case_id]
df["cvss_vector"] = src.cvss_vector.values
df["cvss_v4"] = df.cvss_vector.fillna("").str.startswith("CVSS:4").astype(int)
df["published"] = pd.to_datetime(df.published)
from cvss31 import base_score, band
v3 = df.cvss_vector.map(base_score)
miss = df.cvss_score.isna()
rec = miss & v3.notna()
has3 = v3.notna() & df.cvss_score.notna()
mism = has3 & ((v3 - df.cvss_score).abs() > 0.05)
S_clean = {"cvss_missing": int(miss.sum()), "recovered": int(rec.sum()),
           "recovered_band_match": int((v3[rec].map(band) == df.cvss_severity[rec]).sum()),
           "left_missing": int((miss & ~rec).sum()), "v3_with_score": int(has3.sum()), "score_vector_mismatch": int(mism.sum()),
           "band_flip": int((has3 & (v3.map(band) != df.cvss_severity)).sum()),
           "outcome_flip": int((has3 & ((v3 >= 7).astype(int) != df.high_impact)).sum())}
df["cvss_score_raw"] = df.cvss_score
df.loc[rec, "cvss_score"] = v3[rec]

# CWE groups (current-practice triage baseline)
CWE_GROUPS = [("Command injection", {"77", "78", "88"}),
              ("Code injection", {"94", "95", "1336", "79"}),
              ("Path traversal / link following", {"22", "23", "59", "61", "641", "73"}),
              ("Access control / authentication", {"284", "285", "287", "288", "306", "862", "863", "269",
                                                    "276", "732", "1188", "639", "346", "942", "352", "940"}),
              ("Information exposure", {"200", "201", "212", "312", "319", "522", "532", "538", "552",
                                        "668", "310", "322", "297"}),
              ("Untrusted input / prompt injection", {"20", "74", "116", "150", "1427", "1426", "184", "178",
                                                     "183", "436", "693", "807"}),
              ("Untrusted configuration / inclusion", {"15", "829", "426", "427", "494", "506", "1385",
                                                       "749", "501", "356", "350", "696", "515", "377",
                                                       "367", "918", "601"})]


def cwe_group(s):
    ids = [x.strip().replace("CWE-", "") for x in str(s).split(";") if x.strip()]
    for name, g in CWE_GROUPS:
        if any(i in g for i in ids):
            return name
    return "Other"


df["cwe_group"] = df.cwe_ids.map(cwe_group)

# =====================================================================================
# EDA
# =====================================================================================
num = pd.DataFrame({"CVSS base score": df.cvss_score,
                    "Description length (characters)": src.description.str.len().values,
                    "CWE identifiers per case": df.cwe_ids.fillna("").map(lambda s: len([x for x in s.split(";") if x])),
                    "Domains present (final labels)": df.n_domains,
                    "Governance Compliance Score (%)": df.gcs})
desc = num.describe().T
desc["skew"] = num.skew()
desc.round(2).to_csv(TAB / "eda_numeric_summary.csv")
S["cleaning"] = S_clean
S["eda"] = {"n": N, "high_impact": int(df.high_impact.sum()), "hi_rate": df.high_impact.mean(),
            "years": df.year.value_counts().to_dict(), "products": df["product"].nunique(),
            "ecosystem": int(df.ecosystem.sum()),
            "first": str(df.published.min().date()), "last": str(df.published.max().date()),
            "severity": df.cvss_severity.value_counts().to_dict(),
            "cvss_median": float(df.cvss_score.median()), "cvss_missing": int(df.cvss_score.isna().sum())}

# association of covariates with outcome
assoc = []
for col, lab in [("cwe_group", "CWE group"), ("ecosystem", "Ecosystem component"),
                 ("year_2026", "Published in 2026"), ("user_interaction_required", "User interaction required"),
                 ("cvss_v4", "CVSS version 4.0")]:
    t = pd.crosstab(df[col], df.high_impact)
    chi, p, dof, e = stats.chi2_contingency(t, correction=False)
    assoc.append({"Characteristic": lab, "Levels": t.shape[0], "chi2": chi, "df": dof, "p": p,
                  "cramers_v": np.sqrt(chi / (t.values.sum() * (min(t.shape) - 1))),
                  "min_expected": e.min(), "n": int(t.values.sum())})
pd.DataFrame(assoc).round(4).to_csv(TAB / "eda_association.csv", index=False)
cw = df.groupby("cwe_group").high_impact.agg(["count", "mean"]).sort_values("count", ascending=False)
cw.round(3).to_csv(TAB / "eda_cwe_group.csv")

# Figure: quarterly disclosures by severity
q = df.assign(q=df.published.dt.to_period("Q").astype(str)).pivot_table(
    index="q", columns="cvss_severity", values="case_id", aggfunc="count", fill_value=0)
allq = pd.period_range(df.published.min().to_period("Q"), df.published.max().to_period("Q"), freq="Q").astype(str)
q = q.reindex(allq, fill_value=0)
q = q[[c for c in ["LOW", "MEDIUM", "HIGH", "CRITICAL"] if c in q]]
q = q.loc[q.index >= "2025Q1"]
fig, ax = plt.subplots(figsize=(7.2, 3.6))
bottom = np.zeros(len(q))
cols = {"LOW": AQUA, "MEDIUM": BLUE, "HIGH": ORANGE, "CRITICAL": RED}
for c in q.columns:
    ax.bar(q.index, q[c], bottom=bottom, color=cols[c], label=c.title(), edgecolor="white", linewidth=1.2, width=0.7)
    bottom += q[c].values
for i, v in enumerate(bottom):
    ax.text(i, v + 1, int(v), ha="center", va="bottom", fontsize=8, color=INK2)
ax.set_ylabel("Advisories published")
ax.set_xlabel("Quarter of publication")
ax.legend(title="CVSS severity", ncol=4, loc="upper left", fontsize=8, title_fontsize=8)
ax.grid(axis="x", visible=False)
save(fig, "fig_eda_quarterly")

# Figure: CVSS distribution and product
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4))
axes[0].hist(df.cvss_score.dropna(), bins=np.arange(1.5, 10.6, 0.5), color=BLUE, edgecolor="white")
axes[0].axvline(7, color=INK2, ls="--", lw=1)
axes[0].text(7.05, axes[0].get_ylim()[1] * 0.92, "High threshold (7.0)", fontsize=7.5, color=INK2)
axes[0].set_xlabel("CVSS base score")
axes[0].set_ylabel("Cases")
axes[0].set_title("(a) Score distribution", fontsize=9.5, loc="left")
pc = df.groupby("product").high_impact.agg(["sum", "count"]).sort_values("count").tail(10)
y = np.arange(len(pc))
axes[1].barh(y, pc["sum"], color=ORANGE, label="High-impact", edgecolor="white")
axes[1].barh(y, pc["count"] - pc["sum"], left=pc["sum"], color=BLUE, label="Other", edgecolor="white")
axes[1].set_yticks(y, pc.index, fontsize=8)
axes[1].set_xlabel("Cases")
axes[1].set_title("(b) Ten most frequent products", fontsize=9.5, loc="left")
axes[1].legend(fontsize=8, loc="lower right")
axes[1].grid(axis="y", visible=False)
save(fig, "fig_eda_cvss_product")

# Figure: high-impact rate by CWE group with Wilson CI
cwr = []
for g_, sub in df.groupby("cwe_group"):
    p, lo, hi = wilson(sub.high_impact.sum(), len(sub))
    cwr.append((g_, len(sub), p, lo, hi))
cwr = pd.DataFrame(cwr, columns=["group", "n", "p", "lo", "hi"]).sort_values("p")
fig, ax = plt.subplots(figsize=(7.0, 3.4))
yy = np.arange(len(cwr))
ax.errorbar(cwr.p, yy, xerr=[cwr.p - cwr.lo, cwr.hi - cwr.p], fmt="o", color=BLUE, ecolor=INK2, capsize=3, ms=6)
ax.axvline(df.high_impact.mean(), color=ORANGE, ls="--", lw=1)
ax.set_yticks(yy, [f"{g_} (n = {n})" for g_, n in zip(cwr.group, cwr.n)], fontsize=8)
ax.set_xlabel("Share of cases rated High or Critical (Wilson 95% CI)")
ax.set_xlim(0, 1.02)
save(fig, "fig_eda_cwe_rate")

# =====================================================================================
# RQ1 coverage and prevalence
# =====================================================================================
k = int(df.covered.sum())
p, lo, hi = wilson(k, N)
bt = stats.binomtest(k, N, 0.80, alternative="greater")
S["rq1"] = {"covered": k, "n": N, "p": p, "lo": lo, "hi": hi, "binom_p": bt.pvalue,
            "uncovered": df.loc[df.covered == 0, "case_id"].tolist()}
prev = []
for d in range(1, 9):
    row = {"Domain": f"D{d} {DOM_NAME[d]}", "Family": FAMILY[d]}
    for name in ("coder1", "coder2", "llm", "gold"):
        kk = int(codes[name][f"d{d}"].sum())
        row[f"{name}_n"] = kk
        row[f"{name}_pct"] = 100 * kk / N
    pp, l_, h_ = wilson(row["gold_n"], N)
    row["gold_lo"], row["gold_hi"] = 100 * l_, 100 * h_
    prev.append(row)
prev = pd.DataFrame(prev)
prev.round(1).to_csv(TAB / "rq1_domain_prevalence.csv", index=False)
cov_by = {nm: (int(codes[nm].covered.sum()), 100 * codes[nm].covered.mean()) for nm in codes}
S["rq1"]["coverage_by_source"] = cov_by
S["rq1"]["mean_domains"] = {nm: float(codes[nm].n_domains.mean()) for nm in codes}
# breach frequency per control (final labels)
ctrl_rows = []
for c in range(1, 21):
    col = f"c{c:02d}"
    app = df[col].notna().sum()
    br = (df[col] == 1).sum()
    ctrl_rows.append({"control": f"C{c:02d}", "applicable": int(app), "breached": int(br),
                      "breach_rate_applicable": br / app if app else np.nan, "share_all_cases": br / N})
ctrl = pd.DataFrame(ctrl_rows)
ctrl.round(3).to_csv(TAB / "rq1_control_breaches.csv", index=False)
co = np.zeros((8, 8), int)
for i in range(8):
    for j in range(8):
        co[i, j] = int(((df[f"d{i+1}"] == 1) & (df[f"d{j+1}"] == 1)).sum())
pd.DataFrame(co, index=[f"D{i}" for i in range(1, 9)], columns=[f"D{i}" for i in range(1, 9)]).to_csv(TAB / "rq1_cooccurrence.csv")

# Figure: domain prevalence by label source
fig, ax = plt.subplots(figsize=(7.4, 3.9))
x = np.arange(8)
w = 0.2
for i, (nm, lab, colr) in enumerate([("coder1", "Coder 1", BLUE), ("coder2", "Coder 2", ORANGE),
                                     ("llm", "LLM coder", AQUA), ("gold", "Final (majority)", INK)]):
    ax.bar(x + (i - 1.5) * w, prev[f"{nm}_pct"], width=w - 0.02, color=colr, label=lab)
ax.errorbar(x + 1.5 * w, prev.gold_pct, yerr=[prev.gold_pct - prev.gold_lo, prev.gold_hi - prev.gold_pct],
            fmt="none", ecolor=INK2, capsize=2, lw=0.8)
ax.set_xticks(x, [f"D{d}" for d in range(1, 9)])
ax.set_ylabel("Cases with domain present (%)")
ax.set_ylim(0, 100)
ax.legend(ncol=4, fontsize=8, loc="upper right")
ax.grid(axis="x", visible=False)
save(fig, "fig_rq1_prevalence")

# =====================================================================================
# RQ2 family x user interaction
# =====================================================================================
d2 = df[df.user_interaction_required.notna()].copy()
d2["family"] = d2.primary_domain.map(lambda v: FAMILY[int(v)])
tab = pd.crosstab(d2.family, d2.user_interaction_required.astype(int))
tab.columns = ["No interaction (UI:N)", "Interaction required"]
chi, pv, dof, exp = stats.chi2_contingency(tab, correction=False)
V = np.sqrt(chi / (tab.values.sum() * (min(tab.shape) - 1)))
resid = (tab.values - exp) / np.sqrt(exp)
rng = np.random.default_rng(SEED)
fam, ui = d2.family.values, d2.user_interaction_required.astype(int).values
obs_chi = chi
mc = 0
for _ in range(10000):
    t = pd.crosstab(fam, rng.permutation(ui)).values
    e = t.sum(1, keepdims=True) * t.sum(0, keepdims=True) / t.sum()
    mc += np.sum((t - e) ** 2 / e) >= obs_chi - 1e-12
mc_p = (mc + 1) / 10001
fam_m = np.where(fam == "D", "A", fam)  # merge sparse family D into A
tm = pd.crosstab(fam_m, ui)
chi_m, p_m, dof_m, _ = stats.chi2_contingency(tm, correction=False)
out2 = tab.copy()
out2["Total"] = out2.sum(1)
out2["Pct interaction"] = 100 * out2["Interaction required"] / out2["Total"]
out2["Std residual (UI:N)"] = resid[:, 0]
out2.index = [f"{i} {FAMILY_NAME[i]}" for i in out2.index]
out2.round(2).to_csv(TAB / "rq2_crosstab.csv")
# power at observed n for w = .25
from scipy.stats import ncx2
crit = stats.chi2.ppf(0.95, dof)
power = 1 - ncx2.cdf(crit, dof, len(d2) * 0.25 ** 2)
S["rq2"] = {"n": int(len(d2)), "chi2": chi, "df": int(dof), "p": pv, "V": V, "mc_p": mc_p,
            "min_expected": float(exp.min()), "n_exp_lt5": int((exp < 5).sum()),
            "merged_chi2": chi_m, "merged_df": int(dof_m), "merged_p": p_m, "power_w25": power,
            "table": tab.to_dict()}
# also by each coder's labels
alt = []
for nm in ("coder1", "coder2", "llm"):
    cc = codes[nm].set_index("case_id").loc[d2.case_id]
    f = cc.primary_domain.map(lambda v: FAMILY[int(v)]).values
    t = pd.crosstab(f, ui)
    c_, p_, dd, e_ = stats.chi2_contingency(t, correction=False)
    alt.append({"labels": nm, "chi2": c_, "df": dd, "p": p_, "V": np.sqrt(c_ / (t.values.sum() * (min(t.shape) - 1)))})
pd.DataFrame(alt).round(4).to_csv(TAB / "rq2_by_source.csv", index=False)
S["rq2"]["by_source"] = alt

fig, ax = plt.subplots(figsize=(6.6, 3.0))
yy = np.arange(len(out2))
ax.barh(yy, out2["Pct interaction"], color=ORANGE, label="Interaction required", edgecolor="white")
ax.barh(yy, 100 - out2["Pct interaction"], left=out2["Pct interaction"], color=BLUE,
        label="No interaction (UI:N)", edgecolor="white")
for i, (pc_, n_) in enumerate(zip(out2["Pct interaction"], out2["Total"])):
    ax.text(2, i, f"{pc_:.0f}%", va="center", color="white", fontsize=8, fontweight="bold")
    ax.text(101, i, f"n = {n_}", va="center", fontsize=8, color=INK2)
ax.set_yticks(yy, out2.index, fontsize=8)
ax.set_xlim(0, 112)
ax.set_xlabel("Share of cases (%)")
ax.legend(ncol=2, fontsize=8, loc="upper center", bbox_to_anchor=(0.45, 1.18))
ax.grid(axis="y", visible=False)
save(fig, "fig_rq2_family_ui")

# =====================================================================================
# RQ3 inferential model
# =====================================================================================
def zs(x):
    return (x - x.mean()) / x.std(ddof=0)


df["gcs_z"] = zs(df.gcs)
m = df.gcs.notna()
d3 = df[m].copy()
X = d3[["gcs_z", "ecosystem", "n_domains", "year_2026"]].values
names = ["GCS (per SD)", "Ecosystem component", "Number of domains", "Published in 2026"]
fit = logit_fit(X, d3.high_impact.values, names)
fit_cl = logit_fit(X, d3.high_impact.values, names, cluster=d3["product"].values)
hl = hosmer_lemeshow(d3.high_impact.values, fit["pred"])
g1 = d3.gcs + 1
bt_fit = logit_fit(np.column_stack([X, g1 * np.log(g1)]), d3.high_impact.values, names + ["GCS x ln(GCS)"])
vifs = vif(X)
rq3 = pd.DataFrame({"Term": fit["names"], "b": fit["b"], "SE": fit["se"], "z": fit["z"], "p": fit["p"],
                    "OR": fit["or"], "OR_lo": fit["lo"], "OR_hi": fit["hi"],
                    "cluster_SE": fit_cl["se"], "cluster_lo": fit_cl["lo"], "cluster_hi": fit_cl["hi"],
                    "cluster_p": fit_cl["p"]})
rq3.round(4).to_csv(TAB / "rq3_logit_model2.csv", index=False)
S["rq3"] = {"n": fit["n"], "lr": fit["lr"], "lr_df": fit["lr_df"], "lr_p": fit["lr_p"],
            "mcfadden": fit["mcfadden"], "hl": hl, "box_tidwell_p": float(bt_fit["p"][-1]),
            "vif": vifs, "events_low": int((d3.high_impact == 0).sum()),
            "gcs_mean_hi": float(d3.loc[d3.high_impact == 1, "gcs"].mean()),
            "gcs_mean_lo": float(d3.loc[d3.high_impact == 0, "gcs"].mean()),
            "gcs_median_hi": float(d3.loc[d3.high_impact == 1, "gcs"].median()),
            "gcs_median_lo": float(d3.loc[d3.high_impact == 0, "gcs"].median()),
            "gcs_sd": float(d3.gcs.std(ddof=0))}
mw = stats.mannwhitneyu(d3.loc[d3.high_impact == 1, "gcs"], d3.loc[d3.high_impact == 0, "gcs"])
S["rq3"]["mw_u"], S["rq3"]["mw_p"] = float(mw.statistic), float(mw.pvalue)

# sensitivity
sens = []


def add_sens(label, xcol, data, extra=None, cluster=False):
    dd = data.dropna(subset=[xcol])
    cols_ = [xcol, "ecosystem", "n_domains", "year_2026"] + (extra or [])
    Xs = dd[cols_].values.astype(float)
    f = logit_fit(Xs, dd.high_impact.values, cols_, cluster=dd["product"].values if cluster else None)
    sens.append({"Specification": label, "n": f["n"], "OR": f["or"][1], "lo": f["lo"][1], "hi": f["hi"][1],
                 "p": f["p"][1], "McFadden": f["mcfadden"]})


add_sens("A. Final labels, GCS (Model 2)", "gcs_z", d3)
add_sens("B. As A, product-clustered SE", "gcs_z", d3, cluster=True)
add_sens("C. As A, plus CVSS 4.0 covariate", "gcs_z", d3, extra=["cvss_v4"])
for nm, lab in (("coder1", "D. Coder 1 labels"), ("coder2", "E. Coder 2 labels"), ("llm", "F. LLM labels")):
    cc = derive(codes[nm]).set_index("case_id").loc[df.case_id]
    tmp = df.copy()
    tmp["n_domains"] = cc.n_domains.values
    tmp["g"] = zs(pd.Series(cc.gcs.values, index=tmp.index))
    add_sens(lab, "g", tmp)
tmp = d3.copy()
tmp["nb"] = zs(tmp.n_breached.astype(float))
add_sens("G. Breached-control count (per SD) instead of GCS", "nb", tmp)
sens = pd.DataFrame(sens)
sens.round(4).to_csv(TAB / "rq3_sensitivity.csv", index=False)
S["rq3"]["sensitivity"] = sens.round(4).to_dict("records")

# Figure: GCS by impact
fig, ax = plt.subplots(figsize=(5.6, 3.4))
groups = [d3.loc[d3.high_impact == 0, "gcs"], d3.loc[d3.high_impact == 1, "gcs"]]
bp = ax.boxplot(groups, widths=0.45, patch_artist=True, showfliers=False,
                medianprops=dict(color=INK, lw=1.6))
for patch, colr in zip(bp["boxes"], [BLUE, ORANGE]):
    patch.set_facecolor(colr); patch.set_alpha(0.35); patch.set_edgecolor(colr)
for i, g_ in enumerate(groups):
    jitter = np.random.default_rng(1).uniform(-0.15, 0.15, len(g_))
    ax.scatter(np.full(len(g_), i + 1) + jitter, g_, s=9, color=[BLUE, ORANGE][i], alpha=0.6, lw=0)
ax.set_xticks([1, 2], [f"Low or Medium\n(n = {len(groups[0])})", f"High or Critical\n(n = {len(groups[1])})"])
ax.set_ylabel("Governance Compliance Score (%)")
ax.grid(axis="x", visible=False)
save(fig, "fig_rq3_gcs_box")

# Figure: sensitivity forest
fig, ax = plt.subplots(figsize=(6.6, 3.2))
yy = np.arange(len(sens))[::-1]
ax.errorbar(sens.OR, yy, xerr=[sens.OR - sens.lo, sens.hi - sens.OR], fmt="o", color=BLUE, ecolor=INK2, capsize=3)
ax.axvline(1, color=ORANGE, ls="--", lw=1)
ax.set_yticks(yy, sens.Specification, fontsize=8)
ax.set_xscale("log")
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 3], ["0.5", "0.75", "1", "1.5", "2", "3"])
ax.set_xlabel("Odds ratio per SD (log scale, 95% CI)")
save(fig, "fig_rq3_sensitivity")

# =====================================================================================
# RQ3 predictive models: hold-out split + CV
# =====================================================================================
for c in range(1, 21):
    df[f"b{c:02d}"] = (df[f"c{c:02d}"] == 1).astype(int)
cwe_d = pd.get_dummies(df.cwe_group, prefix="cwe", dtype=int)
cwe_cols = list(cwe_d.columns)
df = pd.concat([df, cwe_d], axis=1)
COV = ["ecosystem", "n_domains", "year_2026"]
ACEG = DOM + [f"b{c:02d}" for c in range(1, 21)] + ["gcs"] + COV
FEATS = {"M0": COV, "M1": COV, "M2": ["gcs"] + COV, "M3": cwe_cols + ["ecosystem", "year_2026"],
         "M4": ACEG, "M5": ACEG, "M6": ACEG, "M7": ACEG + cwe_cols}
LABEL = {"M0": "M0 Majority-class baseline", "M1": "M1 Logistic: covariates only",
         "M2": "M2 Logistic: GCS + covariates", "M3": "M3 Logistic: CWE group (current triage)",
         "M4": "M4 Random forest: ACEG profile", "M5": "M5 Gradient boosting: ACEG profile",
         "M6": "M6 Neural network (MLP): ACEG profile", "M7": "M7 Random forest: ACEG + CWE"}
FEAT_DESC = {"M0": "None (class prior)", "M1": "Component type, number of domains, 2026",
             "M2": "GCS + M1 covariates", "M3": "CWE-group indicators, component type, 2026",
             "M4": "8 domains, 20 control breaches, GCS, covariates", "M5": "As M4",
             "M6": "As M4 (standardized)", "M7": "M4 features + CWE groups"}
SHORT = {"M1": "M1 Logit: covariates", "M2": "M2 Logit: GCS", "M3": "M3 Logit: CWE group",
         "M4": "M4 RF: ACEG", "M5": "M5 GBM: ACEG", "M6": "M6 MLP: ACEG", "M7": "M7 RF: ACEG + CWE"}
y = df.high_impact.values
idx_tr, idx_te = train_test_split(np.arange(N), test_size=0.25, stratify=y, random_state=SEED)
S["split"] = {"train": len(idx_tr), "test": len(idx_te), "train_hi": int(y[idx_tr].sum()),
              "test_hi": int(y[idx_te].sum())}
pd.DataFrame({"case_id": df.case_id, "split": np.where(np.isin(np.arange(N), idx_te), "test", "train")}).to_csv(
    OUT / "train_test_split.csv", index=False)

inner = StratifiedKFold(5, shuffle=True, random_state=SEED)
base = {
    "M0": (DummyClassifier(strategy="prior"), None),
    "M1": (make_pipeline(StandardScaler(), LogisticRegression(penalty=None, max_iter=2000)), None),
    "M2": (make_pipeline(StandardScaler(), LogisticRegression(penalty=None, max_iter=2000)), None),
    "M3": (make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)), None),
    "M4": (RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=SEED),
           {"max_depth": [3, 5, None], "min_samples_leaf": [1, 3, 5], "max_features": ["sqrt", 0.5]}),
    "M5": (HistGradientBoostingClassifier(random_state=SEED, class_weight="balanced"),
           {"learning_rate": [0.03, 0.1], "max_depth": [2, 3], "max_iter": [100, 300], "min_samples_leaf": [5, 10]}),
    "M6": (make_pipeline(StandardScaler(), MLPClassifier(max_iter=3000, early_stopping=False, random_state=SEED)),
           {"mlpclassifier__hidden_layer_sizes": [(16,), (32, 16), (64, 32)],
            "mlpclassifier__alpha": [1e-3, 1e-2, 1e-1, 1.0]}),
    "M7": (RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=SEED),
           {"max_depth": [3, 5, None], "min_samples_leaf": [1, 3, 5], "max_features": ["sqrt", 0.5]}),
}
rep = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
perf, fitted, test_prob, best_params = [], {}, {}, {}
for mk, (est, grid) in base.items():
    Xall = df[FEATS[mk]].values.astype(float)
    Xtr, Xte, ytr, yte = Xall[idx_tr], Xall[idx_te], y[idx_tr], y[idx_te]
    if grid:
        gs = GridSearchCV(est, grid, scoring="roc_auc", cv=inner, n_jobs=-1).fit(Xtr, ytr)
        model, best_params[mk] = gs.best_estimator_, gs.best_params_
    else:
        model = clone(est).fit(Xtr, ytr)
    # repeated CV on the training set (model selection estimate)
    cv_auc = []
    for tr, va in rep.split(Xtr, ytr):
        mm = clone(model).fit(Xtr[tr], ytr[tr])
        cv_auc.append(roc_auc_score(ytr[va], mm.predict_proba(Xtr[va])[:, 1]))
    ptr = model.predict_proba(Xtr)[:, 1]
    pte = model.predict_proba(Xte)[:, 1]
    btr, bte = binclass(ytr, (ptr >= 0.5).astype(int)), binclass(yte, (pte >= 0.5).astype(int))
    auc_te = roc_auc_score(yte, pte) if len(np.unique(pte)) > 1 else 0.5
    ci = boot_ci(lambda a, b: roc_auc_score(a, b) if len(np.unique(a)) > 1 and len(np.unique(b)) > 1 else np.nan,
                 yte, pte, B=2000)
    perf.append({"Model": LABEL[mk], "key": mk, "Features": FEAT_DESC[mk],
                 "train_auc": roc_auc_score(ytr, ptr) if len(np.unique(ptr)) > 1 else 0.5,
                 "train_acc": btr["acc"], "train_bal_acc": btr["bal_acc"], "train_f1": btr["f1"],
                 "cv_auc": np.mean(cv_auc), "cv_auc_sd": np.std(cv_auc),
                 "test_auc": auc_te, "test_auc_lo": ci[0], "test_auc_hi": ci[1],
                 "test_acc": bte["acc"], "test_bal_acc": bte["bal_acc"], "test_prec": bte["prec"],
                 "test_rec": bte["rec"], "test_f1": bte["f1"], "test_spec": bte["spec"],
                 "test_brier": brier_score_loss(yte, pte), "train_brier": brier_score_loss(ytr, ptr)})
    fitted[mk], test_prob[mk] = model, pte
perf = pd.DataFrame(perf)
perf.round(3).to_csv(TAB / "model_performance.csv", index=False)
S["best_params"] = {k: {kk: str(vv) for kk, vv in v.items()} for k, v in best_params.items()}
cand = perf[perf.key != "M0"]
best_key = cand.sort_values(["cv_auc"], ascending=False).iloc[0]["key"]
S["best_model"] = best_key
S["perf"] = perf.round(4).to_dict("records")
yte = y[idx_te]
# paired bootstrap of AUC difference on test set: best vs M2 and M3
rngb = np.random.default_rng(SEED)
diffs = {"M2": [], "M3": []}
for _ in range(2000):
    ii = rngb.integers(0, len(yte), len(yte))
    if len(np.unique(yte[ii])) < 2:
        continue
    for comp in diffs:
        diffs[comp].append(roc_auc_score(yte[ii], test_prob[best_key][ii]) - roc_auc_score(yte[ii], test_prob[comp][ii]))
S["auc_diff"] = {c: {"mean": float(np.mean(v)), "lo": float(np.percentile(v, 2.5)),
                     "hi": float(np.percentile(v, 97.5)), "p_le0": float(np.mean(np.array(v) <= 0))}
                 for c, v in diffs.items()}

# full-data repeated CV for every model (robustness)
cvfull = []
for mk, (est, grid) in base.items():
    Xall = df[FEATS[mk]].values.astype(float)
    model = fitted[mk]
    aucs, bals = [], []
    for tr, va in rep.split(Xall, y):
        mm = clone(model).fit(Xall[tr], y[tr])
        pp_ = mm.predict_proba(Xall[va])[:, 1]
        aucs.append(roc_auc_score(y[va], pp_) if len(np.unique(pp_)) > 1 else 0.5)
        bals.append(binclass(y[va], (pp_ >= .5).astype(int))["bal_acc"])
    cvfull.append({"Model": LABEL[mk], "auc": np.mean(aucs), "auc_sd": np.std(aucs),
                   "bal_acc": np.mean(bals), "bal_acc_sd": np.std(bals)})
pd.DataFrame(cvfull).round(3).to_csv(TAB / "model_cv_fulldata.csv", index=False)
S["cv_full"] = pd.DataFrame(cvfull).round(4).to_dict("records")

# ROC figure (test set)
fig, ax = plt.subplots(figsize=(5.6, 4.6))
style = {"M1": (INK2, ":"), "M2": (BLUE, "--"), "M3": (YELLOW, "-."), "M4": (ORANGE, "-"),
         "M5": (VIOLET, "-"), "M6": (AQUA, "-"), "M7": (RED, "-")}
for mk, (colr, ls) in style.items():
    fpr, tpr, _ = roc_curve(yte, test_prob[mk])
    a = perf.loc[perf.key == mk, "test_auc"].iloc[0]
    ax.plot(fpr, tpr, color=colr, ls=ls, lw=2 if mk == best_key else 1.4,
            label=f"{SHORT[mk]} (AUC = {a:.2f})")
ax.plot([0, 1], [0, 1], color=GRID, lw=1.2, ls="--", label="M0 baseline (AUC = 0.50)")
ax.set_xlabel("False positive rate (1 - specificity)")
ax.set_ylabel("True positive rate (recall)")
ax.legend(fontsize=7.5, loc="lower right")
ax.set_aspect("equal")
save(fig, "fig_model_roc")

# confusion matrices: best model vs M2 on test set
fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.1))
for axx, mk in zip(axes, [best_key, "M2"]):
    cm = confusion_matrix(yte, (test_prob[mk] >= 0.5).astype(int), labels=[0, 1])
    axx.imshow(cm, cmap="Blues", vmin=0, vmax=cm.max() * 1.15)
    for i in range(2):
        for j in range(2):
            axx.text(j, i, cm[i, j], ha="center", va="center", fontsize=13,
                     color="white" if cm[i, j] > cm.max() * 0.6 else INK)
    axx.set_xticks([0, 1], ["Pred. low", "Pred. high"])
    axx.set_yticks([0, 1], ["Actual low", "Actual high"])
    axx.set_title(SHORT[mk] + (" (best)" if mk == best_key else ""), fontsize=9)
    axx.grid(False)
save(fig, "fig_model_confusion")
S["cm_best"] = confusion_matrix(yte, (test_prob[best_key] >= 0.5).astype(int)).tolist()
S["cm_m2"] = confusion_matrix(yte, (test_prob["M2"] >= 0.5).astype(int)).tolist()

# permutation importance of best model (test set) and RF impurity for reference
Xte_b = df[FEATS[best_key]].values.astype(float)[idx_te]
pi = permutation_importance(fitted[best_key], Xte_b, yte, scoring="roc_auc", n_repeats=50, random_state=SEED)
imp = pd.DataFrame({"feature": FEATS[best_key], "mean": pi.importances_mean, "sd": pi.importances_std}).sort_values(
    "mean", ascending=False)
imp.round(4).to_csv(TAB / "model_permutation_importance.csv", index=False)
S["importance_top"] = imp.head(10).round(4).to_dict("records")
CNAME = {"b01": "C01 least privilege", "b02": "C02 approval gate", "b03": "C03 execution isolation",
         "b04": "C04 policy limits", "b05": "C05 workspace trust", "b06": "C06 faithful disclosure",
         "b07": "C07 action logs", "b08": "C08 untrusted-input isolation", "b09": "C09 tool/MCP allowlist",
         "b10": "C10 secret protection", "b11": "C11 egress limits", "b12": "C12 release integrity",
         "b13": "C13 security testing gate", "b14": "C14 no auto-exec of config", "b15": "C15 named owner",
         "b16": "C16 reversible actions", "b17": "C17 incident response", "b18": "C18 autonomy matched to risk",
         "b19": "C19 human review", "b20": "C20 capability disclosure", "gcs": "GCS",
         "n_domains": "Number of domains", "ecosystem": "Ecosystem component", "year_2026": "Published in 2026"}
CNAME.update({f"d{d}": f"D{d} {DOM_NAME[d].split(' and')[0].split(' ')[0]}" for d in range(1, 9)})
CNAME.update({c: "CWE: " + c.replace("cwe_", "") for c in cwe_cols})
top = imp.head(10)[::-1]
fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.barh(np.arange(len(top)), top["mean"], xerr=top["sd"], color=BLUE, ecolor=INK2, capsize=2, edgecolor="white")
ax.set_yticks(np.arange(len(top)), [CNAME.get(f, f) for f in top.feature], fontsize=8)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("Mean drop in test AUC when the feature is shuffled (50 repeats)")
ax.grid(axis="y", visible=False)
save(fig, "fig_model_importance")

# =====================================================================================
# RQ4 human versus LLM coding
# =====================================================================================
c1, c2, ll = (codes[k].set_index("case_id").loc[df.case_id].apply(pd.to_numeric, errors="coerce") for k in ("coder1", "coder2", "llm"))
pair_rows, cons_rows = [], []
items = DOM + ["covered"]
for it in items:
    a, b, l = c1[it].values.astype(int), c2[it].values.astype(int), ll[it].values.astype(int)
    row = {"Item": it.upper() if it != "covered" else "Coverage",
           "C1_pct": 100 * a.mean(), "C2_pct": 100 * b.mean(), "LLM_pct": 100 * l.mean()}
    for nm, (u, v) in {"C1_C2": (a, b), "C1_LLM": (a, l), "C2_LLM": (b, l)}.items():
        row[f"k_{nm}"] = kappa(u, v)
        row[f"po_{nm}"] = np.mean(u == v)
    row["fleiss"] = fleiss(np.column_stack([a, b, l]), [0, 1])
    pair_rows.append(row)
    agree = a == b
    ref, pred = a[agree], l[agree]
    bc = binclass(ref, pred)
    kk = kappa(ref, pred) if len(np.unique(ref)) > 1 else np.nan
    ci = boot_ci(lambda r, p_: kappa(r, p_) if len(np.unique(r)) > 1 else np.nan, ref, pred, B=2000)
    cons_rows.append({"Item": row["Item"], "n_consensus": int(agree.sum()), "pos_ref": int(ref.sum()),
                      "pos_llm": int(pred.sum()), "acc": bc["acc"], "prec": bc["prec"], "rec": bc["rec"],
                      "f1": bc["f1"], "kappa": kk, "k_lo": ci[0], "k_hi": ci[1], "fp": int(bc["fp"]), "fn": int(bc["fn"])})
pairs = pd.DataFrame(pair_rows)
cons = pd.DataFrame(cons_rows)
# primary domain (8 categories)
pa, pb, pl = (x.primary_domain.values.astype(int) for x in (c1, c2, ll))
prim = {"k_C1_C2": kappa(pa, pb), "k_C1_LLM": kappa(pa, pl), "k_C2_LLM": kappa(pb, pl),
        "po_C1_C2": np.mean(pa == pb), "po_C1_LLM": np.mean(pa == pl), "po_C2_LLM": np.mean(pb == pl),
        "fleiss": fleiss(np.column_stack([pa, pb, pl]), list(range(1, 9)))}
pairs = pd.concat([pairs, pd.DataFrame([{"Item": "Primary domain", **prim}])], ignore_index=True)
agp = pa == pb
cons = pd.concat([cons, pd.DataFrame([{"Item": "Primary domain", "n_consensus": int(agp.sum()),
                                        "acc": np.mean(pl[agp] == pa[agp]), "kappa": kappa(pa[agp], pl[agp]),
                                        "k_lo": boot_ci(kappa, pa[agp], pl[agp])[0],
                                        "k_hi": boot_ci(kappa, pa[agp], pl[agp])[1]}])], ignore_index=True)
pairs.round(3).to_csv(TAB / "rq4_pairwise_kappa.csv", index=False)
cons.round(3).to_csv(TAB / "rq4_llm_vs_consensus.csv", index=False)

# pooled domain-cell evaluation with case-cluster bootstrap
A = c1[DOM].values.astype(int); B = c2[DOM].values.astype(int); L = ll[DOM].values.astype(int)


def pooled(Ai, Bi, Li):
    mask = Ai == Bi
    return kappa(Ai[mask], Li[mask])


pk = pooled(A, B, L)
rngp = np.random.default_rng(SEED)
bs = []
for _ in range(2000):
    ii = rngp.integers(0, N, N)
    bs.append(pooled(A[ii], B[ii], L[ii]))
bs = np.array(bs)
mask = A == B
pb_ = binclass(A[mask], L[mask])
hh = kappa(A.ravel(), B.ravel())
bs_hh = []
for _ in range(2000):
    ii = rngp.integers(0, N, N)
    bs_hh.append(kappa(A[ii].ravel(), B[ii].ravel()))
S["rq4"] = {"pooled_kappa": pk, "pooled_lo": float(np.percentile(bs, 2.5)), "pooled_hi": float(np.percentile(bs, 97.5)),
            "p_le_60": float(np.mean(bs <= 0.60)), "pooled_cells": int(mask.sum()),
            "pooled_acc": pb_["acc"], "pooled_prec": pb_["prec"], "pooled_rec": pb_["rec"], "pooled_f1": pb_["f1"],
            "pooled_fp": int(pb_["fp"]), "pooled_fn": int(pb_["fn"]),
            "hh_pooled_kappa": hh, "hh_lo": float(np.percentile(bs_hh, 2.5)), "hh_hi": float(np.percentile(bs_hh, 97.5)),
            "c1_llm_pooled": kappa(A.ravel(), L.ravel()), "c2_llm_pooled": kappa(B.ravel(), L.ravel()),
            "fleiss_pooled": fleiss(np.column_stack([A.ravel(), B.ravel(), L.ravel()]), [0, 1]),
            "primary": prim, "unanimous_cases": int(((A == B) & (B == L)).all(1).sum())}
# 5 domains where both humans use the code (exclude D3, D7 where Coder 2 never codes present)
use = [0, 1, 3, 4, 5, 7]
S["rq4"]["pooled_kappa_6dom"] = pooled(A[:, use], B[:, use], L[:, use])
# GCS agreement
g1, g2, gl = c1.gcs.values, c2.gcs.values, ll.gcs.values
S["rq4"]["gcs"] = {"r_C1_C2": stats.spearmanr(g1, g2).statistic, "r_C1_LLM": stats.spearmanr(g1, gl).statistic,
                   "r_C2_LLM": stats.spearmanr(g2, gl).statistic,
                   "mad_C1_C2": float(np.mean(np.abs(g1 - g2))), "mad_C1_LLM": float(np.mean(np.abs(g1 - gl))),
                   "mad_C2_LLM": float(np.mean(np.abs(g2 - gl)))}
# control-level agreement among applicable controls
ctl = []
for c in CTRL:
    a, b, l = c1[c].values, c2[c].values, ll[c].values
    ok = ~np.isnan(a) & ~np.isnan(b) & ~np.isnan(l) & (a == b)
    if ok.sum() >= 5:
        ctl.append((c, int(ok.sum()), np.mean(l[ok] == a[ok])))
S["rq4"]["control_agreement"] = ctl
allA = np.concatenate([c1[c].values for c in CTRL]); allB = np.concatenate([c2[c].values for c in CTRL])
allL = np.concatenate([ll[c].values for c in CTRL])
ok = ~np.isnan(allA) & ~np.isnan(allB) & ~np.isnan(allL) & (allA == allB)
S["rq4"]["control_pooled"] = {"cells": int(ok.sum()), "acc": float(np.mean(allA[ok] == allL[ok])),
                              "kappa": kappa(allA[ok], allL[ok])}
ok2 = ~np.isnan(allA) & ~np.isnan(allB)
S["rq4"]["control_hh"] = {"cells": int(ok2.sum()), "acc": float(np.mean(allA[ok2] == allB[ok2])),
                          "kappa": kappa(allA[ok2], allB[ok2])}

# Figure: kappa heatmap
H = pairs.set_index("Item")[["k_C1_C2", "k_C1_LLM", "k_C2_LLM"]]
fig, ax = plt.subplots(figsize=(5.4, 4.6))
Hv = H.values.astype(float)
im = ax.imshow(np.nan_to_num(Hv, nan=0), cmap="Blues", vmin=-0.1, vmax=1, aspect="auto")
for i in range(Hv.shape[0]):
    for j in range(Hv.shape[1]):
        v = Hv[i, j]
        ax.text(j, i, "n/a" if np.isnan(v) else f"{v:.2f}", ha="center", va="center", fontsize=8.5,
                color="white" if (not np.isnan(v) and v > 0.6) else INK)
ax.set_xticks([0, 1, 2], ["Coder 1 vs\nCoder 2", "Coder 1 vs\nLLM", "Coder 2 vs\nLLM"], fontsize=8)
ylabs = [f"{it} {DOM_NAME[int(it[1])].split(' and')[0]}" if it.startswith("D") else it for it in H.index]
ax.set_yticks(range(len(H)), ylabs, fontsize=8)
ax.grid(False)
cb = fig.colorbar(im, ax=ax, fraction=0.04)
cb.set_label("Cohen's kappa", fontsize=8)
save(fig, "fig_rq4_kappa_heatmap")

# Figure: LLM vs consensus per domain (precision/recall/kappa)
cd = cons[cons.Item.str.startswith("D")].copy()
fig, ax = plt.subplots(figsize=(7.0, 3.3))
x = np.arange(len(cd))
for i, (col_, lab, colr) in enumerate([("prec", "Precision", BLUE), ("rec", "Recall", ORANGE), ("kappa", "Cohen's kappa", AQUA)]):
    ax.bar(x + (i - 1) * 0.26, cd[col_].fillna(0), width=0.24, color=colr, label=lab)
ax.axhline(0.60, color=INK2, ls="--", lw=1)
ax.text(len(cd) - 0.5, 0.62, "kappa = .60", fontsize=7.5, color=INK2, ha="right")
ax.set_xticks(x, [f"{it}\n(n = {n})" for it, n in zip(cd.Item, cd.n_consensus)], fontsize=8)
ax.set_ylim(0, 1.05)
ax.set_ylabel("Score against human consensus")
ax.legend(ncol=3, fontsize=8, loc="upper left")
ax.grid(axis="x", visible=False)
save(fig, "fig_rq4_llm_consensus")

# =====================================================================================
# Save deployable model artefacts (scorecard service)
# =====================================================================================
final_feats = FEATS[best_key]
final_model = clone(fitted[best_key]).fit(df[final_feats].values.astype(float), y)
m2_full = clone(fitted["M2"]).fit(df[FEATS["M2"]].values.astype(float), y)
(ROOT / "models").mkdir(exist_ok=True)
with open(ROOT / "models/aceg_risk_model.pkl", "wb") as fh:
    pickle.dump({"model": final_model, "features": final_feats, "key": best_key, "label": LABEL[best_key],
                 "cwe_groups": CWE_GROUPS, "trained_on": int(N), "seed": SEED,
                 "base_rate": float(y.mean())}, fh)
with open(ROOT / "models/aceg_risk_model_holdout.pkl", "wb") as fh:
    pickle.dump({"model": fitted[best_key], "features": final_feats, "key": best_key, "label": LABEL[best_key] + " (training split only)",
                 "cwe_groups": CWE_GROUPS, "trained_on": int(len(idx_tr)), "seed": SEED,
                 "base_rate": float(y[idx_tr].mean())}, fh)
pd.DataFrame({"case_id": df.case_id.values[idx_te], "high_impact": yte,
              **{f"p_{k}": v for k, v in test_prob.items()}}).to_csv(OUT / "test_predictions.csv", index=False)
S["deploy_features"] = final_feats
json.dump(S, open(OUT / "summary.json", "w"), indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(perf[["key", "train_auc", "cv_auc", "test_auc", "test_bal_acc", "test_f1", "test_brier"]].round(3).to_string())
print("best", best_key)
print(json.dumps({k: S[k] for k in ("rq1", "rq2")}, indent=1, default=str)[:3000])
print(rq3.round(3).to_string())
print(sens.round(3).to_string())
print(pairs.round(3).to_string())
print(cons.round(3).to_string())
print({k: v for k, v in S["rq4"].items() if k != "control_agreement"})
