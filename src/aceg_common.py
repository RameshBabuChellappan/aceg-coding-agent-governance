"""Shared constants and helpers for the final ACEG analysis (QM640 final report)."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DOM = [f"d{i}" for i in range(1, 9)]
CTRL = [f"c{i:02d}" for i in range(1, 21)]
LINK = {1: [1, 2, 3], 2: [4, 5], 3: [6, 7], 4: [8, 9], 5: [10, 11],
        6: [12, 13, 14], 7: [15, 16, 17], 8: [18, 19, 20]}
CTRL2DOM = {c: d for d, cs in LINK.items() for c in cs}
FAMILY = {1: "A", 2: "A", 8: "A", 4: "B", 6: "B", 5: "C", 3: "D", 7: "D"}
FAMILY_NAME = {"A": "Agency and oversight", "B": "Input and code integrity",
               "C": "Data protection", "D": "Transparency and accountability"}
DOM_NAME = {1: "Agency and action control", 2: "Instruction and boundary adherence",
            3: "Transparency and honest reporting", 4: "Input trust and goal integrity",
            5: "Secrets and data protection", 6: "Code and supply-chain integrity",
            7: "Accountability and recoverability", 8: "Human oversight and reliance"}
CAUSAL_ORDER = [4, 6, 2, 1, 8, 5, 3, 7]   # tie-break: earliest point in the causal chain


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Add n_domains, n_applicable, n_breached, gcs and domain_family to a coded frame."""
    out = df.copy()
    out["n_domains"] = out[DOM].sum(axis=1).astype(int)
    app = np.zeros(len(out), dtype=int)
    br = np.zeros(len(out), dtype=int)
    for d, cs in LINK.items():
        pres = out[f"d{d}"].values == 1
        app += pres * len(cs)
        for c in cs:
            br += (pres & (out[f"c{c:02d}"].values == 1)).astype(int)
    out["n_applicable"], out["n_breached"] = app, br
    out["gcs"] = np.where(app > 0, 100 * (app - br) / np.maximum(app, 1), np.nan)
    out["domain_family"] = out["primary_domain"].map(lambda p: FAMILY.get(int(p)) if pd.notna(p) else None)
    return out
