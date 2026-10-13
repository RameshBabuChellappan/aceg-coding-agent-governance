"""Attach SYNTHETIC codes to the real frozen cases, only to test that src/04_analysis.py runs end to end.

The source fields (product, CVSS, high_impact, user interaction) are real; every coded value is random.
The output is NOT a study result. Never report it.
Run: python tests/make_synthetic.py && python src/04_analysis.py tests/synthetic_cases.csv
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
d = pd.read_csv("data/processed/cases_to_code.csv")
LINK = {1: [1, 2, 3], 2: [4, 5], 3: [6, 7], 4: [8, 9], 5: [10, 11], 6: [12, 13, 14], 7: [15, 16, 17], 8: [18, 19, 20]}
prev = [0.55, 0.30, 0.08, 0.45, 0.25, 0.40, 0.08, 0.20]
for i in d.index:
    doms = [int(rng.random() < p) for p in prev]
    if sum(doms) == 0:
        doms[rng.integers(0, 8)] = 1
    for k, v in enumerate(doms, 1):
        d.loc[i, f"d{k}"] = v
    present = [k for k in range(1, 9) if doms[k - 1]]
    d.loc[i, "primary_domain"] = int(rng.choice(present))
    for k in range(1, 21):
        d.loc[i, f"c{k:02d}"] = "NA"
    for k in present:
        for c in LINK[k]:
            d.loc[i, f"c{c:02d}"] = str(int(rng.random() < 0.45))
    d.loc[i, "covered"] = int(rng.random() < 0.9)
    for k in range(1, 9):
        d.loc[i, f"llm_d{k}"] = doms[k - 1] if rng.random() < 0.88 else 1 - doms[k - 1]
    d.loc[i, "llm_primary_domain"] = d.loc[i, "primary_domain"] if rng.random() < 0.8 else int(rng.integers(1, 9))
    for k in range(1, 21):
        d.loc[i, f"llm_c{k:02d}"] = d.loc[i, f"c{k:02d}"] if rng.random() < 0.85 else "0"
d.to_csv("tests/synthetic_cases.csv", index=False)
print("tests/synthetic_cases.csv written (synthetic codes, for testing only)")
