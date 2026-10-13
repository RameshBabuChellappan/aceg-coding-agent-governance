"""Week 2 (and weekly checks) — inter-coder reliability from the coding workbook.

Run: python src/05_pilot_kappa.py            pilot rows only (batch "W2 pilot")
     python src/05_pilot_kappa.py --all      every row both coders have finished
Out: outputs/pilot_kappa.csv or outputs/interrater_kappa.csv, and a printed summary.
Rule: any domain with kappa < .60 on the pilot is reworded in docs/codebook.md (log it in docs/framework_changelog.md).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).parent))
from coding_io import CTRL, DOM, LINK, coded, derive, load  # noqa: E402

ALL = "--all" in sys.argv
cases, c1, c2, _ = load()
mask = coded(c1) & coded(c2)
if not ALL:
    mask &= cases["batch"].eq("W2 pilot")
idx = mask[mask].index
label = "all finished rows" if ALL else "pilot rows"
if len(idx) == 0:
    sys.exit(f"No {label} have been coded by both coders yet.")
a, b = derive(c1.loc[idx]), derive(c2.loc[idx])


def kappa(x, y):
    x, y = list(x), list(y)
    if len(set(x) | set(y)) == 1:
        return 1.0  # perfect agreement on a constant
    return cohen_kappa_score(x, y)


rows = []
for d in DOM:
    k = kappa(a[d], b[d])
    rows.append({"item": d.upper(), "n": len(idx), "agreement": np.mean(a[d].values == b[d].values), "kappa": k,
                 "flag": "revise wording (kappa < .60)" if k < 0.60 else "ok"})
k = kappa(a["primary_domain"], b["primary_domain"])
rows.append({"item": "primary domain", "n": len(idx), "agreement": np.mean(a["primary_domain"].values == b["primary_domain"].values),
             "kappa": k, "flag": "revise wording (kappa < .60)" if k < 0.60 else "ok"})
k = kappa(a["covered"], b["covered"])
rows.append({"item": "covered", "n": len(idx), "agreement": np.mean(a["covered"].values == b["covered"].values), "kappa": k,
             "flag": "revise wording (kappa < .60)" if k < 0.60 else "ok"})
# control status where both coders treated the control as applicable
xs, ys = [], []
for i in idx:
    for d, cs in LINK.items():
        if c1.at[i, d] == 1 and c2.at[i, d] == 1:
            for c in cs:
                xs.append(c1.at[i, f"c{c:02d}"])
                ys.append(c2.at[i, f"c{c:02d}"])
if xs:
    k = kappa(xs, ys)
    rows.append({"item": "control status (jointly applicable)", "n": len(xs), "agreement": np.mean(np.array(xs) == np.array(ys)),
                 "kappa": k, "flag": "revise wording (kappa < .60)" if k < 0.60 else "ok"})
both = pd.DataFrame({"g1": a["gcs"].values, "g2": b["gcs"].values}).dropna()
res = pd.DataFrame(rows)
out = Path("outputs") / ("interrater_kappa.csv" if ALL else "pilot_kappa.csv")
out.parent.mkdir(exist_ok=True)
res.to_csv(out, index=False)
print(f"Inter-coder reliability on {len(idx)} {label}\n")
print(res.round(3).to_string(index=False))
if len(both) > 2:
    print(f"\nGCS: Spearman rho = {both.corr(method='spearman').iloc[0, 1]:.3f}; "
          f"mean absolute difference = {np.mean(np.abs(both.g1 - both.g2)):.1f} points")
flag = res[res.flag != "ok"]["item"].tolist()
print("\nItems to revise:", ", ".join(flag) if flag else "none — proceed to Week 3")
print(f"Saved {out}")
