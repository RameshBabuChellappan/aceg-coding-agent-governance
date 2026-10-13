"""Step 2 — apply the eligibility criteria and freeze the analysis dataset.

Input : data/interim/candidates.csv (from 01_collect.py)
        docs/screening_decisions.csv (record-level exclusions and component-type overrides, with reasons)
Output: data/processed/cases_to_code.csv   eligible cases numbered CA-001 ...
        outputs/screening_flow.csv          PRISMA-style counts
Run   : python src/02_screen.py
"""
import re
from pathlib import Path

import pandas as pd

CAND = Path("data/interim/candidates.csv")
DEC = Path("docs/screening_decisions.csv")
OUT = Path("data/processed/cases_to_code.csv")
FLOW = Path("outputs/screening_flow.csv")

# Third-party tools that wrap, extend or serve coding agents (bridges, MCP servers, harnesses, UIs, routers,
# guards, CI workflows). Everything else that passes screening is the coding-agent product itself.
ECOSYSTEM = re.compile(
    r"claude-code-router|claude-code-ui|claude code templates|claude-code-cache-fix|openclaw-claude-bridge|agenticmail|"
    r"agentapi|claudehookbridge|cortex|ruflo|knowns|harness-opencode|codex harness|ai sdk|omnigent|paperclip|"
    r"gemini-mcp-tool|gemini-bridge|aider-mcp|cline-mcp-memory-bank|roo-code-memory-bank|mcp memory keeper|"
    r"mcp documentation server|token optimizer mcp|context7|chrome-devtools-mcp|coderag|gryph|safeinstall|ouroboros|"
    r"nono|fastmcp|mlflow|todesktop|nnu-net|language servers for aws|kanban|cline hub", re.I)


def main() -> None:
    d = pd.read_csv(CAND)
    d["record_id"] = d["cve_id"].fillna(d["ghsa_id"])
    dec = pd.read_csv(DEC).set_index("record_id")
    d["decision"] = d["record_id"].map(dec["decision"]).fillna("include")
    d["exclusion_reason"] = d["record_id"].map(dec["reason"]).where(d["decision"] == "exclude", "")
    inc = d[d["decision"] == "include"].copy()
    text = inc["title"].fillna("") + " " + inc["description"].fillna("") + " " + inc["packages"].fillna("")
    inc["component_type"] = ["ecosystem" if ECOSYSTEM.search(t) else "agent product" for t in text]
    over = dec[dec["decision"] == "component"]["reason"]
    inc.loc[inc["record_id"].isin(over.index), "component_type"] = inc["record_id"].map(over)
    inc = inc.sort_values(["published", "record_id"]).reset_index(drop=True)
    inc.insert(0, "case_id", [f"CA-{i + 1:03d}" for i in range(len(inc))])
    inc["year"] = inc["published"].str[:4].astype(int)
    inc["high_impact"] = inc["cvss_severity"].isin(["HIGH", "CRITICAL"]).astype(int)
    inc["user_interaction_required"] = (inc["user_interaction"] == "required").astype("Int64").where(inc["user_interaction"].notna())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    inc.drop(columns=["decision", "exclusion_reason"]).to_csv(OUT, index=False)
    flow = pd.DataFrame([
        ("Records identified (GHSA + CVE list, 2023 to freeze)", len(d)),
        ("Excluded: not an AI coding agent or a component it runs", int((d.exclusion_reason.str.startswith("E1", na=False)).sum())),
        ("Excluded: autocomplete-only or no agent capability", int((d.exclusion_reason.str.startswith("E2", na=False)).sum())),
        ("Excluded: insufficient detail to code", int((d.exclusion_reason.str.startswith("E3", na=False)).sum())),
        ("Included (analysis dataset)", len(inc)),
    ], columns=["stage", "n"])
    FLOW.parent.mkdir(exist_ok=True)
    flow.to_csv(FLOW, index=False)
    print(flow.to_string(index=False))
    print(inc["component_type"].value_counts().to_string())
    print(f"high_impact = {inc.high_impact.mean():.3f}; user interaction known = {inc.user_interaction_required.notna().sum()}")


if __name__ == "__main__":
    main()
