#!/usr/bin/env python3
"""ACEG scorecard: score one coded case (JSON) or a batch (CSV) of AI coding-agent advisories.

  python aceg_score.py case.json [--html card.html] [--portable]
  python aceg_score.py cases.csv --batch scored.csv [--portable]

CSV columns: case_id, component_type, year, cwe_ids, domains ("1;4"), primary_domain,
breached_controls ("2;8"), covered. Uses assets/aceg_risk_model.pkl (scikit-learn) when it
loads, otherwise assets/portable_model.json (no dependencies beyond the standard library).
"""
import argparse
import csv
import html
import json
import math
import pickle
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
LINK = {1: [1, 2, 3], 2: [4, 5], 3: [6, 7], 4: [8, 9], 5: [10, 11], 6: [12, 13, 14], 7: [15, 16, 17], 8: [18, 19, 20]}
FAMILY = {1: "A Agency and oversight", 2: "A Agency and oversight", 8: "A Agency and oversight",
          4: "B Input and code integrity", 6: "B Input and code integrity", 5: "C Data protection",
          3: "D Transparency and accountability", 7: "D Transparency and accountability"}
DOMAIN = {1: "Agency and action control", 2: "Instruction and boundary adherence", 3: "Transparency and honest reporting",
          4: "Input trust and goal integrity", 5: "Secrets and data protection", 6: "Code and supply-chain integrity",
          7: "Accountability and recoverability", 8: "Human oversight and reliance"}
CONTROL = {1: ("Least-privilege credentials and tool permissions", "ASI02, ASI03 / MANAGE", "Scope and shorten agent credentials; read-only CI tokens"),
           2: ("Human approval gate for sensitive actions", "ASI02 / MANAGE", "Require approval for shell, network and out-of-workspace writes; patch parser bypasses"),
           3: ("Execution isolation (sandbox)", "ASI05 / MANAGE", "Run agents in container/VM/OS sandbox; no production credentials"),
           4: ("Machine-enforced policy limits", "ASI10 / MANAGE", "Managed deny/allow rules with canonical paths; fail closed"),
           5: ("Workspace trust before execution", "ASI01 / MAP", "Require explicit trust before loading project settings, also in headless mode"),
           6: ("Faithful disclosure of planned actions", "ASI09 / GOVERN", "Show full commands and arguments in approval dialogs"),
           7: ("Tamper-evident action logs", "ASI10 / GOVERN", "Log tool calls and commands to SIEM"),
           8: ("Isolation of untrusted inputs", "ASI01, ASI06 / MANAGE", "Treat repo, web, issue and tool output as untrusted; no shell interpolation"),
           9: ("Allow-listed, integrity-checked tools and MCP servers", "ASI04 / MANAGE", "Allow-list MCP servers by publisher and hash; re-approve on change"),
           10: ("Secret protection", "ASI03 / MANAGE", "Keep secrets out of context and logs; secret manager; 0600 token files"),
           11: ("Network egress limits", "ASI02 / GOVERN", "Exact-host egress allowlist; disable auto image/schema fetch"),
           12: ("Release and extension integrity", "ASI04 / MANAGE", "Verify signatures and provenance of agent artefacts"),
           13: ("Security testing gate", "ASI05 / MEASURE", "Add injection, traversal and sandbox tests to release gate"),
           14: ("No auto-execution of workspace configuration", "ASI05 / MANAGE", "Disable hooks, tasks, fsmonitor and .env routing on repository open"),
           15: ("Named owner and authorization", "ASI08 / GOVERN", "Assign an owner and approval scope to each agent deployment"),
           16: ("Reversible actions", "ASI08 / MANAGE", "Checkpoints and backups; block destructive production operations"),
           17: ("Incident response and patching", "ASI08 / MANAGE", "Patch service-level agreements; replace unsupported tools"),
           18: ("Autonomy matched to risk", "ASI09 / MAP", "Safe defaults; bypass/yolo modes only in disposable sandboxes"),
           19: ("Human review of agent output", "ASI09 / MANAGE", "Human review on agent pull requests and shared-environment commands"),
           20: ("Capability disclosure", "ASI09 / GOVERN", "Document agent permissions and limits for users")}
PRIORITY = [1, 14, 8, 11, 2]
WEAK_FOR_LLM = {1, 2, 3, 7, 8}


def parse_list(v):
    if isinstance(v, list):
        return [int(x) for x in v]
    return [int(x) for x in str(v).replace(",", ";").split(";") if str(x).strip()]


def load_model(force_portable=False):
    port = json.load(open(ASSETS / "portable_model.json"))
    if not force_portable:
        try:
            m = pickle.load(open(ASSETS / "aceg_risk_model.pkl", "rb"))
            return "forest", m, port
        except Exception as exc:  # scikit-learn missing or incompatible
            print(f"[aceg] random forest unavailable ({type(exc).__name__}); using portable model", file=sys.stderr)
    return "portable", None, port


def cwe_group(cwe_ids, groups):
    ids = [x.strip().replace("CWE-", "") for x in str(cwe_ids or "").split(";") if x.strip()]
    for name, g in groups:
        if any(i in set(g) for i in ids):
            return name
    return "Other"


def score(rec, kind, model, port):
    doms = sorted(set(parse_list(rec["domains"])))
    if any(d not in LINK for d in doms):
        raise ValueError("domains must be integers 1-8")
    if not doms:
        raise ValueError("at least one domain must be present")
    br = sorted(set(parse_list(rec.get("breached_controls", []))))
    applicable = [c for d in doms for c in LINK[d]]
    bad = [c for c in br if c not in applicable]
    if bad:
        raise ValueError(f"controls {bad} are not linked to a present domain")
    prim = int(rec.get("primary_domain") or doms[0])
    if prim not in doms:
        raise ValueError("primary_domain must be one of the domains present")
    gcs = 100 * (len(applicable) - len(br)) / len(applicable)
    groups = port["cwe_groups"]
    grp = cwe_group(rec.get("cwe_ids"), groups)
    f = {f"d{d}": float(d in doms) for d in range(1, 9)}
    f.update({f"b{c:02d}": float(c in br) for c in range(1, 21)})
    f.update({"gcs": gcs, "n_domains": float(len(doms)), "ecosystem": float(rec.get("component_type") == "ecosystem"),
              "year_2026": float(int(rec.get("year", 2026)) >= 2026)})
    for name, _ in groups + [["Other", None]]:
        f[f"cwe_{name}"] = float(name == grp)
    if kind == "forest":
        p = float(model["model"].predict_proba([[f.get(k, 0.0) for k in model["features"]]])[0, 1])
        t1, t2, used = 0.80, 0.50, model["label"]
    else:
        z = port["intercept"] + sum(v * f.get(k, 0.0) for k, v in port["coefficients"].items())
        p = 1 / (1 + math.exp(-z))
        t1, t2, used = port["tier_thresholds"]["p1"], port["tier_thresholds"]["p2"], port["model"]
    tier = "P1 fix before agent use" if p >= t1 else "P2 fix this sprint" if p >= t2 else "P3 routine patch cycle"
    order = sorted(br, key=lambda c: (PRIORITY.index(c) if c in PRIORITY else 9, c not in LINK[prim], c))
    return {"case_id": rec.get("case_id"), "title": rec.get("title", ""), "product": rec.get("product", ""),
            "gcs": round(gcs, 1), "controls_held": len(applicable) - len(br), "n_applicable": len(applicable),
            "n_domains": len(doms), "domains": [f"D{d} {DOMAIN[d]}" for d in doms],
            "primary_domain": f"D{prim} {DOMAIN[prim]}", "family": FAMILY[prim], "cwe_group": grp,
            "p_high_impact": round(p, 3), "base_rate": round(port["base_rate"], 3), "priority": tier,
            "remediation_plan": [{"control": f"C{c:02d}", "requirement": CONTROL[c][0], "crosswalk": CONTROL[c][1],
                                  "action": CONTROL[c][2], "priority_control": c in PRIORITY} for c in order],
            "extension_controls": [f"C{c}" for c in parse_list(rec.get("extension_controls", []))],
            "human_review_required": sorted([f"D{d}" for d in doms if d in WEAK_FOR_LLM]) + ["primary_domain"],
            "coverage_gap": int(rec.get("covered", 1)) == 0, "model_used": used}


def to_html(sc):
    e = html.escape
    rows = "".join(f"<tr><td><b>{e(r['control'])}</b>{' ★' if r['priority_control'] else ''}</td><td>{e(r['requirement'])}</td>"
                   f"<td>{e(r['action'])}</td><td>{e(r['crosswalk'])}</td></tr>" for r in sc["remediation_plan"])
    return (f"<!doctype html><meta charset='utf-8'><title>ACEG scorecard {e(str(sc['case_id']))}</title>"
            "<style>body{font-family:Arial,sans-serif;margin:24px;color:#111}td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left;font-size:13px}"
            "table{border-collapse:collapse;width:100%}.k{display:inline-block;margin-right:28px}.v{font-size:24px;font-weight:bold}</style>"
            f"<h2>ACEG scorecard: {e(str(sc['case_id']))} {e(sc['product'])}</h2><p>{e(sc['title'])}</p>"
            f"<div class=k>GCS<div class=v>{sc['gcs']:.0f}%</div>{sc['controls_held']}/{sc['n_applicable']} held</div>"
            f"<div class=k>Domains<div class=v>{sc['n_domains']}</div>{e(sc['primary_domain'])}</div>"
            f"<div class=k>P(high impact)<div class=v>{100*sc['p_high_impact']:.0f}%</div>base rate {100*sc['base_rate']:.0f}%</div>"
            f"<div class=k>Priority<div class=v style='font-size:16px'>{e(sc['priority'])}</div></div>"
            f"<h3>Remediation plan (★ = priority control)</h3><table><tr><th>Control</th><th>Requirement</th><th>Action</th><th>OWASP / NIST</th></tr>{rows}</table>"
            f"<p>Human review required: {', '.join(sc['human_review_required'])}. Model: {e(sc['model_used'])}.</p>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--html")
    ap.add_argument("--batch")
    ap.add_argument("--portable", action="store_true")
    a = ap.parse_args()
    kind, model, port = load_model(a.portable)
    if a.batch:
        out = []
        with open(a.input, newline="", encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                sc = score(rec, kind, model, port)
                out.append({"case_id": sc["case_id"], "gcs": sc["gcs"], "n_domains": sc["n_domains"],
                            "primary_domain": sc["primary_domain"], "p_high_impact": sc["p_high_impact"],
                            "priority": sc["priority"], "breached": ";".join(r["control"] for r in sc["remediation_plan"])})
        with open(a.batch, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0]))
            w.writeheader(); w.writerows(out)
        tiers = {}
        for r in out:
            tiers[r["priority"]] = tiers.get(r["priority"], 0) + 1
        print(json.dumps({"cases": len(out), "priority_counts": tiers, "model_used": kind}, indent=1))
        return
    sc = score(json.load(open(a.input, encoding="utf-8")), kind, model, port)
    print(json.dumps(sc, indent=1))
    if a.html:
        Path(a.html).write_text(to_html(sc), encoding="utf-8")


if __name__ == "__main__":
    main()
