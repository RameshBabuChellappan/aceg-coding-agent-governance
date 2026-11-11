"""Step 10 - ACEG scorecard service (deployment prototype).

Turns one coded advisory into a governance scorecard: Governance Compliance Score (GCS),
breached controls with their OWASP / NIST crosswalk, domain family, and the predicted
probability that the weakness is high-impact (CVSS High or Critical) from the selected model.

Three ways to use it
  python src/10_scorecard_service.py serve            # REST API on http://127.0.0.1:8080
        POST /score   JSON body (see EXAMPLE)  -> JSON scorecard
        GET  /scorecard/<case_id>              -> HTML scorecard for a case in data/aceg.db
        GET  /health
  python src/10_scorecard_service.py demo CA-214      # writes outputs/final/scorecard_CA-214.html
  from importlib import import_module; svc = import_module("10_scorecard_service"); svc.score(record)

The input record is what the ACEG coding skill (docs/aceg_coding_skill.md) returns for a new
advisory, plus the CWE identifiers, component type and publication year from the advisory.
"""
import html
import json
import pickle
import sqlite3
import sys

import numpy as np
import pandas as pd

from aceg_common import ROOT, LINK, FAMILY, FAMILY_NAME, DOM_NAME

import os
MODEL = pickle.load(open(ROOT / os.environ.get("ACEG_MODEL", "models/aceg_risk_model.pkl"), "rb"))
CONTROLS = {
    1: ("Least-privilege credentials and tool permissions", "ASI02, ASI03 / MANAGE"),
    2: ("Human approval gate for sensitive or irreversible actions", "ASI02 / MANAGE"),
    3: ("Execution isolation (sandbox; dev/prod separation)", "ASI05 / MANAGE"),
    4: ("Machine-enforced policy limits (deny rules, ignore files, allowlists)", "ASI10 / MANAGE"),
    5: ("Workspace trust and scope confirmation before execution", "ASI01 / MAP"),
    6: ("Faithful disclosure of planned actions", "ASI09 / GOVERN"),
    7: ("Tamper-evident action logs", "ASI10 / GOVERN"),
    8: ("Isolation and sanitization of untrusted inputs", "ASI01, ASI06 / MANAGE"),
    9: ("Allow-listed, integrity-checked tools and MCP servers", "ASI04 / MANAGE"),
    10: ("Secret scanning, redaction and protected credential storage", "ASI03 / MANAGE"),
    11: ("Network egress limits and data-handling policy", "ASI02 / GOVERN"),
    12: ("Dependency, extension and release integrity verification", "ASI04 / MANAGE"),
    13: ("Security testing gate before release or merge", "ASI05 / MEASURE"),
    14: ("No auto-execution of untrusted workspace configuration", "ASI05 / MANAGE"),
    15: ("Named human owner and authorization for agent actions", "ASI08 / GOVERN"),
    16: ("Reversible actions (checkpoints, backup and rollback)", "ASI08 / MANAGE"),
    17: ("Incident response, patching and disclosure process", "ASI08 / MANAGE"),
    18: ("Autonomy level matched to risk (safe defaults)", "ASI09 / MAP"),
    19: ("Human review of agent-authored changes and commands", "ASI09 / MANAGE"),
    20: ("Capability and limitation disclosure to users", "ASI09 / GOVERN"),
}
EXAMPLE = {"case_id": "NEW-001", "component_type": "agent product", "year": 2026, "cwe_ids": "CWE-78",
           "domains": [1, 2, 4], "primary_domain": 2, "breached_controls": [2, 4, 8]}


def cwe_group(cwe_ids):
    ids = [x.strip().replace("CWE-", "") for x in str(cwe_ids).split(";") if x.strip()]
    for name, g in MODEL["cwe_groups"]:
        if any(i in g for i in ids):
            return name
    return "Other"


def score(rec: dict) -> dict:
    doms = sorted(set(int(d) for d in rec["domains"]))
    if not doms:
        raise ValueError("at least one governance domain must be present")
    br = sorted(set(int(c) for c in rec.get("breached_controls", [])))
    applicable = [c for d in doms for c in LINK[d]]
    bad = [c for c in br if c not in applicable]
    if bad:
        raise ValueError(f"controls {bad} are not linked to a present domain")
    gcs = 100 * (len(applicable) - len(br)) / len(applicable)
    feats = {f"d{d}": int(d in doms) for d in range(1, 9)}
    feats.update({f"b{c:02d}": int(c in br) for c in range(1, 21)})
    feats.update({"gcs": gcs, "n_domains": len(doms), "ecosystem": int(rec.get("component_type") == "ecosystem"),
                  "year_2026": int(int(rec.get("year", 2026)) == 2026)})
    grp = cwe_group(rec.get("cwe_ids", ""))
    for name, _ in MODEL["cwe_groups"] + [("Other", None)]:
        feats[f"cwe_{name}"] = int(name == grp)
    x = np.array([[feats.get(f, 0) for f in MODEL["features"]]], float)
    p = float(MODEL["model"].predict_proba(x)[0, 1])
    tier = ("Priority 1: fix before agent use" if p >= 0.80 else
            "Priority 2: fix this sprint" if p >= 0.50 else "Priority 3: routine patch cycle")
    prim = int(rec.get("primary_domain", doms[0]))
    return {"case_id": rec.get("case_id"), "gcs": round(gcs, 1), "n_domains": len(doms),
            "n_applicable": len(applicable), "n_breached": len(br),
            "domains": [{"code": f"D{d}", "name": DOM_NAME[d]} for d in doms],
            "primary_domain": f"D{prim}", "family": f"{FAMILY[prim]} {FAMILY_NAME[FAMILY[prim]]}",
            "cwe_group": grp,
            "breached_controls": [{"code": f"C{c:02d}", "name": CONTROLS[c][0], "crosswalk": CONTROLS[c][1]} for c in br],
            "controls_held": [f"C{c:02d}" for c in applicable if c not in br],
            "p_high_impact": round(p, 3), "risk_tier": tier, "model": MODEL["label"],
            "base_rate": round(MODEL["base_rate"], 3)}


def record_from_db(case_id):
    con = sqlite3.connect(ROOT / "data/aceg.db")
    r = pd.read_sql("SELECT * FROM v_analysis WHERE case_id = ?", con, params=(case_id,)).iloc[0]
    t = pd.read_sql("SELECT title, product, description FROM cases WHERE case_id = ?", con, params=(case_id,)).iloc[0]
    con.close()
    doms = [d for d in range(1, 9) if r[f"d{d}"] == 1]
    br = [c for c in range(1, 21) if str(r[f"c{c:02d}"]) in ("1", "1.0")]
    rec = {"case_id": case_id, "component_type": r.component_type, "year": int(r.year), "cwe_ids": r.cwe_ids,
           "domains": doms, "primary_domain": int(r.primary_domain), "breached_controls": br}
    title = t.title if isinstance(t.title, str) and t.title else str(t.description)[:110] + "..."
    return rec, {"title": title, "product": t["product"]}


def render_html(sc, meta):
    e = html.escape
    rows = "".join(f"<tr><td class='code'>{e(c['code'])}</td><td>{e(c['name'])}</td><td class='muted'>{e(c['crosswalk'])}</td></tr>"
                   for c in sc["breached_controls"])
    doms = " ".join(f"<span class='chip'>{e(d['code'])} {e(d['name'])}</span>" for d in sc["domains"])
    pct = int(round(100 * sc["p_high_impact"]))
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>ACEG Scorecard</title><style>
body{{font-family:'DejaVu Sans',Arial,sans-serif;background:#f4f3ef;color:#0b0b0b;margin:0;padding:22px}}
.card{{background:#fcfcfb;border:1px solid #e4e3df;border-radius:10px;padding:18px 22px;max-width:920px;margin:auto}}
h1{{font-size:19px;margin:0 0 4px}} .sub{{color:#52514e;font-size:13px;margin-bottom:14px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0 16px}}
.kpi{{border:1px solid #e4e3df;border-radius:8px;padding:10px 12px;background:white}}
.kpi .v{{font-size:26px;font-weight:700}} .kpi .l{{font-size:12px;color:#52514e}}
.bar{{height:8px;background:#e4e3df;border-radius:4px;margin-top:6px}} .bar>div{{height:8px;border-radius:4px;background:#eb6834}}
.chip{{display:inline-block;border:1px solid #2a78d6;color:#1d5aa6;border-radius:12px;padding:2px 9px;margin:2px 4px 2px 0;font-size:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:6px}} td,th{{border-bottom:1px solid #e4e3df;padding:6px 6px;text-align:left}}
th{{color:#52514e;font-weight:600;font-size:12px}} .code{{font-weight:700;color:#b5461b;width:52px}} .muted{{color:#52514e}}
.tier{{display:inline-block;padding:3px 10px;border-radius:12px;background:#fde6dc;color:#9a3412;font-weight:700;font-size:13px}}
h2{{font-size:14px;margin:14px 0 4px}}
</style></head><body><div class='card'>
<h1>ACEG Governance Scorecard &middot; {e(str(sc['case_id']))}</h1>
<div class='sub'>{e(meta.get('product',''))} &middot; {e(meta.get('title',''))}</div>
<div class='kpis'>
<div class='kpi'><div class='l'>Governance Compliance Score</div><div class='v'>{sc['gcs']:.0f}%</div><div class='l'>{sc['n_applicable']-sc['n_breached']} of {sc['n_applicable']} applicable controls held</div></div>
<div class='kpi'><div class='l'>Governance domains implicated</div><div class='v'>{sc['n_domains']}</div><div class='l'>Primary {e(sc['primary_domain'])} &middot; family {e(sc['family'])}</div></div>
<div class='kpi'><div class='l'>Predicted P(high impact)</div><div class='v'>{pct}%</div><div class='bar'><div style='width:{pct}%'></div></div><div class='l'>Portfolio base rate {int(round(100*sc['base_rate']))}%</div></div>
<div class='kpi'><div class='l'>Triage tier</div><div class='v' style='font-size:16px;margin-top:6px'><span class='tier'>{e(sc['risk_tier'])}</span></div><div class='l'>CWE group: {e(sc['cwe_group'])}</div></div>
</div>
<h2>Domains present</h2><div>{doms}</div>
<h2>Breached controls to remediate (OWASP Agentic Top 10 / NIST AI RMF function)</h2>
<table><tr><th>Control</th><th>Requirement</th><th>Crosswalk</th></tr>{rows}</table>
<div class='sub' style='margin-top:12px'>Controls held: {', '.join(sc['controls_held']) or 'none'} &middot; Model: {e(sc['model'])}</div>
</div></body></html>"""


def serve(port=8080):
    from flask import Flask, jsonify, request, Response
    app = Flask("aceg-scorecard")

    @app.get("/health")
    def health():
        return jsonify(status="ok", model=MODEL["label"], trained_on=MODEL["trained_on"])

    @app.post("/score")
    def score_ep():
        try:
            return jsonify(score(request.get_json(force=True)))
        except (ValueError, KeyError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get("/scorecard/<case_id>")
    def card(case_id):
        rec, meta = record_from_db(case_id)
        return Response(render_html(score(rec), meta), mimetype="text/html")

    app.run(host="127.0.0.1", port=port)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if cmd == "serve":
        serve()
    else:
        cid = sys.argv[2] if len(sys.argv) > 2 else "CA-214"
        rec, meta = record_from_db(cid)
        sc = score(rec)
        out = ROOT / f"outputs/final/scorecard_{cid}.html"
        out.write_text(render_html(sc, meta))
        print(json.dumps(sc, indent=1))
        print(json.dumps(score(EXAMPLE), indent=1))
