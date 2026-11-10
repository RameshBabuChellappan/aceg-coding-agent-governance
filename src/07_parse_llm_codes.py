"""Step 7 - expand the LLM coder's compact output into the full coded layout.

Input  data/llm/llm_codes_compact.txt, one line per case:
       case_id | domains present | primary domain | breached controls | covered
Rules  every control linked to a present domain is applicable: listed = 1 (breached),
       unlisted = 0 (not breached); controls of absent domains are NA (codebook section 3).
Output data/processed/llm_codes.csv
"""
import pandas as pd
from aceg_common import ROOT, DOM, CTRL, LINK, derive

rows = []
for line in (ROOT / "data/llm/llm_codes_compact.txt").read_text().splitlines():
    cid, doms, prim, br, cov = [x.strip() for x in line.split("|")]
    doms = [int(x) for x in doms.split(",") if x]
    br = {int(x) for x in br.split(",") if x}
    rec = {"case_id": cid, "primary_domain": int(prim), "covered": int(cov)}
    for d in range(1, 9):
        rec[f"d{d}"] = int(d in doms)
        for c in LINK[d]:
            rec[f"c{c:02d}"] = (1 if c in br else 0) if d in doms else None
    assert rec[f"d{int(prim)}"] == 1, cid
    assert all(rec[f"c{c:02d}"] is not None for c in br), cid
    rows.append(rec)
df = derive(pd.DataFrame(rows)[["case_id"] + DOM + ["primary_domain"] + CTRL + ["covered"]])
df["llm_model"] = "claude-opus-5-5"
df.to_csv(ROOT / "data/processed/llm_codes.csv", index=False)
print(len(df), "cases written; mean domains", round(df.n_domains.mean(), 2))
