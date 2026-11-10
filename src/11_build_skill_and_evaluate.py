"""Step 11 - package the ACEG Governance Skill models and evaluate the skill end to end.

1. Fits a *portable* model: L2-penalized logistic regression on the M7 feature set, exported as
   plain JSON coefficients so the skill can score without scikit-learn or pickle files.
2. Evaluates the fully automated skill path on the 56 held-out test cases: features are built from
   the LLM coder's labels (no human input) and scored by (a) the hold-out random forest and
   (b) the portable logistic model trained on the training split only.
Outputs: skill/aceg-governance/assets/portable_model.json, assets/aceg_risk_model.pkl,
         outputs/final/tables/skill_evaluation.csv, outputs/final/skill_summary.json
"""
import json
import pickle
import shutil
import sqlite3

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import GridSearchCV, RepeatedStratifiedKFold, StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from aceg_common import ROOT, DOM, LINK, derive
from stats_utils import binclass, boot_ci

SEED = 42
SK = ROOT / "skill/aceg-governance"
(SK / "assets").mkdir(parents=True, exist_ok=True)
M = pickle.load(open(ROOT / "models/aceg_risk_model.pkl", "rb"))
MH = pickle.load(open(ROOT / "models/aceg_risk_model_holdout.pkl", "rb"))
FEATS, GROUPS = M["features"], M["cwe_groups"]

con = sqlite3.connect(ROOT / "data/aceg.db")
cases = pd.read_sql("SELECT case_id, component_type, year, cwe_ids, high_impact FROM cases ORDER BY case_id", con)
def _num(df):
    for c in df.columns:
        if c not in ("case_id", "domain_family", "source", "rule_domains", "rule_primary"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


codes = {k: _num(pd.read_sql(f"SELECT * FROM codes_{k} ORDER BY case_id", con)) for k in ("gold", "llm")}
con.close()
split = pd.read_csv(ROOT / "outputs/final/train_test_split.csv").set_index("case_id").loc[cases.case_id, "split"].values


def cwe_group(s):
    ids = [x.strip().replace("CWE-", "") for x in str(s).split(";") if x.strip()]
    for name, g in GROUPS:
        if any(i in g for i in ids):
            return name
    return "Other"


def features(code_df):
    c = derive(code_df.set_index("case_id").loc[cases.case_id].reset_index())
    X = pd.DataFrame({f"d{d}": c[f"d{d}"].astype(int).values for d in range(1, 9)})
    for k in range(1, 21):
        X[f"b{k:02d}"] = (pd.to_numeric(c[f"c{k:02d}"], errors="coerce") == 1).astype(int).values
    X["gcs"] = c.gcs.values
    X["ecosystem"] = (cases.component_type == "ecosystem").astype(int).values
    X["n_domains"] = c.n_domains.values
    X["year_2026"] = (cases.year == 2026).astype(int).values
    grp = cases.cwe_ids.map(cwe_group)
    for name, _ in GROUPS + [("Other", None)]:
        X[f"cwe_{name}"] = (grp == name).astype(int).values
    return X[FEATS].astype(float)


y = cases.high_impact.values
Xg, Xl = features(codes["gold"]), features(codes["llm"])
tr, te = split == "train", split == "test"

# ---- portable logistic model
pipe = make_pipeline(StandardScaler(), LogisticRegression(penalty="l2", max_iter=5000))
gs = GridSearchCV(pipe, {"logisticregression__C": [0.01, 0.03, 0.1, 0.3, 1.0]}, scoring="roc_auc",
                  cv=StratifiedKFold(5, shuffle=True, random_state=SEED)).fit(Xg[tr], y[tr])
best_C = gs.best_params_["logisticregression__C"]
port_tr = gs.best_estimator_
rep = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
cv_full = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(C=best_C, max_iter=5000)), Xg, y,
                          scoring="roc_auc", cv=rep)
port_full = make_pipeline(StandardScaler(), LogisticRegression(C=best_C, max_iter=5000)).fit(Xg, y)
sc, lr = port_full.named_steps["standardscaler"], port_full.named_steps["logisticregression"]
coefs = dict(zip(FEATS, lr.coef_[0] / sc.scale_))
intercept = float(lr.intercept_[0] - np.sum(lr.coef_[0] * sc.mean_ / sc.scale_))
rf_p = M["model"].predict_proba(Xg.values)[:, 1]
pt_p = port_full.predict_proba(Xg)[:, 1]
q1, q2 = np.mean(rf_p >= 0.80), np.mean(rf_p >= 0.50)
tiers = {"p1": float(np.quantile(pt_p, 1 - q1)), "p2": float(np.quantile(pt_p, 1 - q2))}
json.dump({"model": "L2 logistic regression on ACEG + CWE features (portable)", "C": best_C,
           "tier_thresholds": tiers, "note": "Thresholds reproduce the random forest's Priority 1/2 shares on the 223 cases",
           "intercept": intercept, "coefficients": {k: float(v) for k, v in coefs.items()},
           "cwe_groups": [[n, sorted(g)] for n, g in GROUPS], "base_rate": float(y.mean()),
           "trained_on": int(len(y)), "cv_auc_full": float(cv_full.mean()), "cv_auc_sd": float(cv_full.std())},
          open(SK / "assets/portable_model.json", "w"), indent=1)
shutil.copy(ROOT / "models/aceg_risk_model.pkl", SK / "assets/aceg_risk_model.pkl")

# ---- end-to-end evaluation on hold-out test set
rows = []


def ev(label, p, labels):
    yt = y[te]
    b = binclass(yt, (p >= 0.5).astype(int))
    lo, hi = boot_ci(lambda a, q: roc_auc_score(a, q) if len(np.unique(a)) > 1 else np.nan, yt, p, B=2000)
    rows.append({"Pipeline": label, "Labels": labels, "test_auc": roc_auc_score(yt, p), "auc_lo": lo, "auc_hi": hi,
                 "bal_acc": b["bal_acc"], "f1": b["f1"], "rec": b["rec"], "spec": b["spec"],
                 "brier": brier_score_loss(yt, p)})


ev("Random forest (M7), hold-out model", MH["model"].predict_proba(Xg[te].values)[:, 1], "Final (majority) labels")
ev("Random forest (M7), hold-out model", MH["model"].predict_proba(Xl[te].values)[:, 1], "LLM coder only (fully automated)")
ev("Portable logistic, training split", port_tr.predict_proba(Xg[te])[:, 1], "Final (majority) labels")
ev("Portable logistic, training split", port_tr.predict_proba(Xl[te])[:, 1], "LLM coder only (fully automated)")
res = pd.DataFrame(rows)
res.round(3).to_csv(ROOT / "outputs/final/tables/skill_evaluation.csv", index=False)
out = {"portable_C": best_C, "portable_cv_auc": float(cv_full.mean()), "portable_cv_sd": float(cv_full.std()),
       "eval": res.round(4).to_dict("records"),
       "top_coefficients": sorted(((k, float(v)) for k, v in coefs.items()), key=lambda t: -abs(t[1]))[:10]}
json.dump(out, open(ROOT / "outputs/final/skill_summary.json", "w"), indent=1)
print(res.round(3).to_string())
print(out["portable_C"], round(out["portable_cv_auc"], 3), out["top_coefficients"][:6])
