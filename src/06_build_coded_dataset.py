"""End of Week 5 — build data/processed/cases_coded.csv from the coding workbook.

Gold label for each field: the Coder 1 value when both coders agree; otherwise the value the adjudicators typed
on the Gold sheet. The script stops and lists any unresolved or inconsistent rows. If
data/processed/llm_codes.csv exists (src/03_llm_code.py), the LLM columns are merged in.

Run: python src/06_build_coded_dataset.py
Out: data/processed/cases_coded.csv, outputs/interrater_kappa_full.csv, outputs/adjudication_log.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).parent))
from coding_io import DOM, FIELDS, coded, derive, load, norm, problems  # noqa: E402

SRC = Path("data/processed/cases_to_code.csv")
LLM = Path("data/processed/llm_codes.csv")
OUT = Path("data/processed/cases_coded.csv")

cases, c1, c2, typed = load()
n = len(cases)
not_done = (~(coded(c1) & coded(c2))).sum()
if not_done:
    sys.exit(f"{not_done} rows are not yet coded by both coders. Finish coding first.")

gold, log, unresolved = [], [], []
for i in range(n):
    row = {}
    for f in FIELDS:
        v1, v2, vt = c1.at[i, f], c2.at[i, f], typed.at[i, f]
        if vt is not None:
            row[f] = vt
            if v1 != v2:
                log.append({"case_id": cases.at[i, "case_id"], "field": f, "coder1": v1, "coder2": v2, "gold": vt})
        elif v1 == v2:
            row[f] = v1
        else:
            row[f] = None
            unresolved.append(f"{cases.at[i, 'case_id']}:{f}")
    gold.append(row)
if unresolved:
    sys.exit(f"{len(unresolved)} disagreements not adjudicated on the Gold sheet, e.g. {unresolved[:10]}")
gold = pd.DataFrame(gold)
for f in DOM + ["primary_domain", "covered"]:
    gold[f] = gold[f].astype("Int64")
bad = {cases.at[i, "case_id"]: problems(gold.loc[i]) for i in range(n) if problems(gold.loc[i])}
if bad:
    for k, v in list(bad.items())[:20]:
        print(k, v)
    sys.exit(f"{len(bad)} gold rows fail consistency checks (see above). Fix them on the Gold sheet.")

gold = derive(gold)
gold.insert(0, "case_id", cases["case_id"])
gold["coder1_primary_domain"] = c1["primary_domain"].values
gold["coder2_primary_domain"] = c2["primary_domain"].values
gold["gold_primary_domain"] = gold["primary_domain"]

src = pd.read_csv(SRC)
keep = ["case_id", "source", "ghsa_id", "cve_id", "url", "published", "year", "product", "component_type",
        "cvss_severity", "cvss_score", "cvss_vector", "high_impact", "user_interaction_required", "cwe_ids"]
data = src[keep].merge(gold, on="case_id", how="left", validate="one_to_one")
vec = data["cvss_vector"].fillna("")
data.insert(data.columns.get_loc("cvss_vector") + 1, "cvss_version",
            np.where(vec.str.startswith("CVSS:4"), 1, np.where(vec.str.startswith("CVSS:3"), 0, np.nan)))

if LLM.exists():
    llm = pd.read_csv(LLM)
    for c in llm.columns:
        if c.startswith("llm_") and c != "llm_model":
            llm[c] = llm[c].map(norm)
    data = data.merge(llm, on="case_id", how="left", validate="one_to_one")
    print(f"Merged LLM codes for {llm['case_id'].nunique()} cases")
else:
    print("No LLM codes yet (run src/03_llm_code.py); writing gold codes only")

data.to_csv(OUT, index=False)
pd.DataFrame(log).to_csv("outputs/adjudication_log.csv", index=False)

rel = []
for f in DOM + ["primary_domain", "covered"]:
    x, y = c1[f].astype(int), c2[f].astype(int)
    k = 1.0 if len(set(x) | set(y)) == 1 else cohen_kappa_score(x, y)  # constant labels: perfect agreement
    rel.append({"item": f, "agreement": float(np.mean(x == y)), "kappa": k})
pd.DataFrame(rel).to_csv("outputs/interrater_kappa_full.csv", index=False)
print(pd.DataFrame(rel).round(3).to_string(index=False))
print(f"\n{len(log)} adjudicated fields logged; wrote {OUT} ({len(data)} rows, {data.shape[1]} columns)")
