"""Step 4 — statistical analysis, modeling and evaluation for RQ1–RQ4.

Input : data/processed/cases_coded.csv (frozen source fields + gold codes + LLM codes; see docs/data_dictionary.csv)
Output: outputs/rq1_*.csv ... outputs/rq4_*.csv and outputs/summary.txt
Run   : python src/04_analysis.py [path/to/cases_coded.csv]
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, cohen_kappa_score,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "data/processed/cases_coded.csv")
OUT = Path("outputs")
OUT.mkdir(exist_ok=True)
Z = 1.96
DOM = [f"d{i}" for i in range(1, 9)]
LINK = {"d1": [1, 2, 3], "d2": [4, 5], "d3": [6, 7], "d4": [8, 9], "d5": [10, 11],
        "d6": [12, 13, 14], "d7": [15, 16, 17], "d8": [18, 19, 20]}
FAMILY = {1: "A", 2: "A", 8: "A", 4: "B", 6: "B", 5: "C", 3: "D", 7: "D"}
log = []


def say(s=""):
    print(s)
    log.append(s)


def wilson(k, n):
    p = k / n
    den = 1 + Z**2 / n
    centre = (p + Z**2 / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z**2 / (4 * n**2)) / den
    return p, centre - half, centre + half


def compute_gcs(d: pd.DataFrame, prefix: str = "") -> pd.Series:
    """GCS = 100 x (applicable controls not breached) / applicable controls."""
    def one(r):
        app = br = 0
        for dom, cs in LINK.items():
            if int(r[prefix + dom]) != 1:
                continue
            for c in cs:
                app += 1
                br += str(r[f"{prefix}c{c:02d}"]) in ("1", "1.0")
        return 100 * (app - br) / app if app else np.nan
    return d.apply(one, axis=1)


def logit_irls(X, y, iters=50):
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ beta))
        H = X.T @ (X * (p * (1 - p))[:, None])
        step = np.linalg.solve(H, X.T @ (y - p))
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    p = 1 / (1 + np.exp(-X @ beta))
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))
    return beta, np.sqrt(np.diag(cov)), p


def hosmer_lemeshow(y, p, g=10):
    q = pd.qcut(p, g, duplicates="drop")
    t = pd.DataFrame({"y": y, "p": p, "g": q}).groupby("g", observed=True).agg(o=("y", "sum"), e=("p", "sum"), n=("y", "size"))
    hl = (((t.o - t.e) ** 2) / (t.e * (1 - t.e / t.n))).sum()
    return hl, stats.chi2.sf(hl, len(t) - 2)


def vif(X):
    out = []
    for j in range(X.shape[1]):
        others = np.delete(X, j, axis=1)
        A = np.column_stack([np.ones(len(X)), others])
        coef, *_ = np.linalg.lstsq(A, X[:, j], rcond=None)
        r2 = 1 - np.sum((X[:, j] - A @ coef) ** 2) / np.sum((X[:, j] - X[:, j].mean()) ** 2)
        out.append(1 / (1 - r2) if r2 < 1 else np.inf)
    return out


d = pd.read_csv(DATA)
n = len(d)
d["gcs"] = compute_gcs(d)
d["n_domains"] = d[DOM].sum(axis=1)
d["domain_family"] = d["primary_domain"].map(FAMILY)
say(f"Cases analysed: N = {n}")
say(f"High-impact share = {d['high_impact'].mean():.3f}; GCS mean = {d['gcs'].mean():.1f}, median = {d['gcs'].median():.1f}")

# ---------------- RQ1: framework coverage and domain prevalence ----------------
rows = []
for dom in DOM:
    k = int(d[dom].sum())
    p, lo, hi = wilson(k, n)
    rows.append({"domain": dom.upper(), "k": k, "prevalence": p, "ci_low": lo, "ci_high": hi})
k_cov = int(d["covered"].sum())
p, lo, hi = wilson(k_cov, n)
rows.append({"domain": "COVERAGE (FCR)", "k": k_cov, "prevalence": p, "ci_low": lo, "ci_high": hi})
rq1 = pd.DataFrame(rows)
rq1.to_csv(OUT / "rq1_prevalence.csv", index=False)
bt = stats.binomtest(k_cov, n, 0.80, alternative="greater")
say("\nRQ1 prevalence (Wilson 95% CI)\n" + rq1.round(3).to_string(index=False))
say(f"H1: FCR = {p:.3f}; exact one-sided binomial test vs .80: p = {bt.pvalue:.4f}")
d.groupby("product")["gcs"].agg(["count", "mean", "median"]).round(1).to_csv(OUT / "rq1_gcs_by_product.csv")

# ---------------- RQ2: domain family x human interaction ----------------
s = d.dropna(subset=["user_interaction_required"])
tab = pd.crosstab(s["domain_family"], s["user_interaction_required"].astype(int))
chi2, pval, dof, exp = stats.chi2_contingency(tab, correction=False)
v = math.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))
tab.to_csv(OUT / "rq2_crosstab.csv")
((tab - exp) / np.sqrt(exp)).round(2).to_csv(OUT / "rq2_std_residuals.csv")
say("\nRQ2 table (rows = domain family; columns = user interaction required)\n" + tab.to_string())
say(f"chi2({dof}) = {chi2:.2f}, p = {pval:.4f}, Cramer's V = {v:.3f}, min expected = {exp.min():.2f}")
if (exp < 5).any():
    rng = np.random.default_rng(42)
    fam, ui = s["domain_family"].values, s["user_interaction_required"].values
    sims = [stats.chi2_contingency(pd.crosstab(fam, rng.permutation(ui)), correction=False)[0] for _ in range(10000)]
    say(f"Monte Carlo permutation p (10,000 draws) = {np.mean(np.array(sims) >= chi2):.4f}")

# ---------------- RQ3: does compliance predict a high-impact case? ----------------
m = d.dropna(subset=["gcs"]).copy()
m["gcs_z"] = (m["gcs"] - m["gcs"].mean()) / m["gcs"].std(ddof=1)
m["ecosystem"] = (m["component_type"] == "ecosystem").astype(int)
m["year_2026"] = (m["year"] >= 2026).astype(int)
preds = ["gcs_z", "ecosystem", "n_domains", "year_2026"]
Xp = m[preds].astype(float).values
X = np.column_stack([np.ones(len(m)), Xp])
y = m["high_impact"].astype(float).values
beta, se, phat = logit_irls(X, y)
zv = beta / se
coef = pd.DataFrame({"term": ["intercept"] + preds, "beta": beta, "se": se, "z": zv,
                     "p": 2 * stats.norm.sf(np.abs(zv)), "odds_ratio": np.exp(beta),
                     "or_ci_low": np.exp(beta - Z * se), "or_ci_high": np.exp(beta + Z * se)})
coef.to_csv(OUT / "rq3_logit.csv", index=False)
ll = np.sum(y * np.log(phat) + (1 - y) * np.log(1 - phat))
ybar = y.mean()
ll0 = len(y) * (ybar * np.log(ybar) + (1 - ybar) * np.log(1 - ybar))
hl, hl_p = hosmer_lemeshow(y, phat)
cv = cross_val_predict(LogisticRegression(C=np.inf, max_iter=1000), Xp, y,
                       cv=StratifiedKFold(5, shuffle=True, random_state=42), method="predict_proba")[:, 1]
say(f"\nRQ3 logistic regression: high_impact ~ {' + '.join(preds)} (n = {len(m)})")
say(coef.round(4).to_string(index=False))
say(f"VIF = {[round(x, 2) for x in vif(Xp)]}")
say(f"LR chi2({len(preds)}) = {2 * (ll - ll0):.2f}; McFadden R2 = {1 - ll / ll0:.3f}; AUC = {roc_auc_score(y, phat):.3f}; "
    f"5-fold CV AUC = {roc_auc_score(y, cv):.3f}; Brier = {brier_score_loss(y, phat):.3f}; "
    f"accuracy@0.5 = {accuracy_score(y, phat >= 0.5):.3f}; Hosmer-Lemeshow = {hl:.2f} (p = {hl_p:.3f})")
u = stats.mannwhitneyu(m.loc[m.high_impact == 1, "gcs"], m.loc[m.high_impact == 0, "gcs"])
say(f"Secondary: Mann-Whitney U = {u.statistic:.1f}, p = {u.pvalue:.4f}")
events = int(min(y.sum(), len(y) - y.sum()))
say(f"Events per predictor (minority class / predictors) = {events}/{len(preds)} = {events / len(preds):.1f}")

# Sensitivity 1: cluster-robust (sandwich) standard errors, clustered by product
groups = m["product"].astype(str).values
W = phat * (1 - phat)
bread = np.linalg.inv(X.T @ (X * W[:, None]))
meat = np.zeros((X.shape[1], X.shape[1]))
for g in np.unique(groups):
    s = X[groups == g].T @ (y[groups == g] - phat[groups == g])
    meat += np.outer(s, s)
G, N, K = len(np.unique(groups)), len(y), X.shape[1]
se_cl = np.sqrt(np.diag(bread @ meat @ bread) * G / (G - 1) * (N - 1) / (N - K))
say(f"Sensitivity (SE clustered by product, {G} clusters): OR(gcs_z) = {np.exp(beta[1]):.3f} "
    f"[{np.exp(beta[1] - Z * se_cl[1]):.3f}, {np.exp(beta[1] + Z * se_cl[1]):.3f}]")

# Sensitivity 2: add CVSS version (4.0 vs 3.x), since severity bands are shared but scoring rules differ
m["cvss_v4"] = m["cvss_vector"].fillna("").str.startswith("CVSS:4").astype(int)
X2 = np.column_stack([X, m["cvss_v4"].values])
b2, se2, _ = logit_irls(X2, y)
say(f"Sensitivity (adding cvss_v4): OR(gcs_z) = {np.exp(b2[1]):.3f} [{np.exp(b2[1] - Z * se2[1]):.3f}, {np.exp(b2[1] + Z * se2[1]):.3f}]")

# Linearity of the logit for GCS: Box-Tidwell term (gcs+1)*ln(gcs+1)
bt_term = (m["gcs"] + 1) * np.log(m["gcs"] + 1)
b3, se3, _ = logit_irls(np.column_stack([X, bt_term.values]), y)
say(f"Box-Tidwell test for GCS: coefficient = {b3[-1]:.4f}, p = {2 * stats.norm.sf(abs(b3[-1] / se3[-1])):.4f} "
    "(p >= .05 supports linearity in the logit)")

# Sensitivity 3: linear regression of the CVSS base score on the same predictors (cases with a numeric score)
s3 = m.dropna(subset=["cvss_score"])
Xs = np.column_stack([np.ones(len(s3)), s3[preds].astype(float).values])
ys = s3["cvss_score"].astype(float).values
bs, *_ = np.linalg.lstsq(Xs, ys, rcond=None)
res = ys - Xs @ bs
sig2 = res @ res / (len(ys) - Xs.shape[1])
se_s = np.sqrt(np.diag(sig2 * np.linalg.inv(Xs.T @ Xs)))
p_s = 2 * stats.t.sf(abs(bs[1] / se_s[1]), len(ys) - Xs.shape[1])
say(f"Sensitivity (OLS on CVSS base score, n = {len(ys)}): b(gcs_z) = {bs[1]:.3f} points, SE = {se_s[1]:.3f}, p = {p_s:.4f}")

# Machine-learning benchmark: random forest on domain and control-breach indicators, stratified 5-fold CV
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402

breach = pd.DataFrame({f"c{c:02d}": (m[f"c{c:02d}"].astype(str).isin(["1", "1.0"])).astype(int) for c in range(1, 21)},
                      index=m.index)
F = pd.concat([m[DOM].astype(int), breach, m[["gcs", "ecosystem", "year_2026"]]], axis=1)
rf = RandomForestClassifier(n_estimators=500, min_samples_leaf=5, class_weight="balanced", random_state=42)
cv_rf = cross_val_predict(rf, F.values, y, cv=StratifiedKFold(5, shuffle=True, random_state=42), method="predict_proba")[:, 1]
rf.fit(F.values, y)
imp = permutation_importance(rf, F.values, y, scoring="roc_auc", n_repeats=50, random_state=42)
imp_df = (pd.DataFrame({"feature": F.columns, "importance_mean": imp.importances_mean, "importance_sd": imp.importances_std})
          .sort_values("importance_mean", ascending=False))
imp_df.to_csv(OUT / "rq3_rf_importance.csv", index=False)
say(f"ML benchmark: random forest 5-fold CV AUC = {roc_auc_score(y, cv_rf):.3f} "
    f"(logistic regression 5-fold CV AUC = {roc_auc_score(y, cv):.3f}); Brier = {brier_score_loss(y, cv_rf):.3f}")
say("Top features by permutation importance:\n" + imp_df.head(8).round(4).to_string(index=False))

# ---------------- RQ4: LLM pipeline vs human gold labels ----------------
if not all(f"llm_{x}" in d for x in DOM + ["primary_domain"]):
    say("\nRQ4 skipped: no LLM codes in the data yet (run src/03_llm_code.py, then src/06_build_coded_dataset.py)")
else:
    rows = []
    for dom in DOM:
        g, l = d[dom].astype(int), d[f"llm_{dom}"].astype(int)
        rows.append({"domain": dom.upper(), "kappa": cohen_kappa_score(g, l),
                     "precision": precision_score(g, l, zero_division=0), "recall": recall_score(g, l, zero_division=0),
                     "f1": f1_score(g, l, zero_division=0)})
    rq4 = pd.DataFrame(rows)
    rq4.to_csv(OUT / "rq4_per_domain.csv", index=False)
    g, l = d["primary_domain"].astype(int), d["llm_primary_domain"].astype(int)
    _, alo, ahi = wilson(int((g == l).sum()), n)
    kap = cohen_kappa_score(g, l)
    rng = np.random.default_rng(42)
    boots = []
    for _ in range(2000):
        idx = rng.integers(0, n, n)
        boots.append(cohen_kappa_score(g.values[idx], l.values[idx]))
    klo, khi = np.percentile(boots, [2.5, 97.5])
    say("\nRQ4 LLM pipeline vs gold labels (per domain)\n" + rq4.round(3).to_string(index=False))
    say(f"Primary domain: accuracy = {accuracy_score(g, l):.3f} (Wilson 95% CI {alo:.3f}-{ahi:.3f}); kappa = {kap:.3f} "
        f"(bootstrap 95% CI {klo:.3f}-{khi:.3f}); macro-F1 = {f1_score(g, l, average='macro'):.3f}")
    say(f"H4 (kappa > .60): {'supported' if klo > 0.60 else 'not supported'} (CI lower bound {klo:.3f})")
    if "llm_c01" in d:
        d["llm_gcs"] = compute_gcs(d, prefix="llm_")
        both = d[["gcs", "llm_gcs"]].dropna()
        say(f"GCS agreement: Spearman rho = {stats.spearmanr(both.gcs, both.llm_gcs)[0]:.3f}; "
            f"mean absolute difference = {np.mean(np.abs(both.gcs - both.llm_gcs)):.1f} points")

(OUT / "summary.txt").write_text("\n".join(log))
