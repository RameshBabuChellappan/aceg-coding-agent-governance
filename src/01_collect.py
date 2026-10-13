"""Step 1 — build the candidate table from two public sources downloaded with git.

Sources (both public, no account needed):
  * GitHub Advisory Database  https://github.com/github/advisory-database  (CC BY 4.0)
  * CVE List V5 (CVE Program) https://github.com/CVEProject/cvelistV5      (CVE Terms of Use)

Download (about 6 GB in total; done once, then frozen):
  git clone --depth 1 https://github.com/github/advisory-database.git data/raw/advisory-database
  git clone --depth 1 --filter=blob:none --sparse https://github.com/CVEProject/cvelistV5.git data/raw/cvelistV5
  git -C data/raw/cvelistV5 sparse-checkout set cves/2023 cves/2024 cves/2025 cves/2026

Run:  python src/01_collect.py
Out:  data/interim/candidates.csv  (one row per unique vulnerability; GHSA and CVE merged on CVE ID)
"""
import csv
import json
import os
import re
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("data/interim/candidates.csv")
START = "2023-01-01"

# Coding-agent products (first match wins). Each pattern is checked against summary + first 600 characters
# of the description + affected product/package names.
PRODUCTS = [
    ("Claude Code", r"claude code|claude-code|claude agent sdk"),
    ("GitHub Copilot", r"github copilot|copilot chat|copilot (cli|coding agent|for (visual studio|vs ?code|jetbrains|xcode|eclipse))|visual studio code.{0,40}copilot|copilot.{0,40}visual studio"),
    ("Cursor", r"cursor is a code editor|\bcursor (ide|editor|agent|cli)\b|\bin cursor\b|cursor (versions?|before|prior to) ?\d|anysphere"),
    ("OpenAI Codex", r"codex cli|openai codex|@openai/codex|\bcodex\b.{0,40}(workspace|sandbox|cli|desktop)"),
    ("Gemini CLI", r"gemini cli|gemini-cli|google gemini code assist"),
    ("Cline", r"\bcline\b"),
    ("Roo Code", r"roo[ -]?code|roo-cline|roocodeinc"),
    ("Kilo Code", r"kilo[ -]?code"),
    ("Windsurf/Codeium", r"windsurf|codeium"),
    ("Kiro", r"\bkiro (ide|cli|is|agent)|amazon kiro|in kiro\b|kiro (before|versions?)"),
    ("Amazon Q Developer", r"amazon q developer|amazon q for (vs ?code|visual studio|jetbrains|command line)|q developer cli"),
    ("Aider", r"\baider\b"),
    ("OpenHands", r"openhands|opendevin|all-hands-ai"),
    ("OpenCode", r"\bopencode\b(?! systems)|sst/opencode|opencode-ai"),
    ("Goose", r"block goose|codename goose|goose (ai agent|cli|desktop)|block/goose"),
    ("Qwen Code", r"qwen code|qwen-code"),
    ("Crush", r"charmbracelet/crush|\bcrush (cli|agent)"),
    ("Continue", r"continuedev|continue\.dev"),
    ("Tabnine", r"tabnine"),
    ("Sourcegraph Cody/Amp", r"sourcegraph (cody|amp)|\bcody (ai|for vs ?code)|\bampcode\b"),
    ("JetBrains AI/Junie", r"jetbrains (ai assistant|junie)|\bjunie\b"),
    ("Zed", r"zed (editor|agent)\b.{0,80}(\bai\b|agent|assistant|llm)|zed industries.{0,80}(\bai\b|agent)"),
    ("Trae", r"\btrae (ide|ai|agent)|bytedance trae"),
    ("Augment Code", r"augment code|augmentcode"),
    ("Devin", r"\bdevin (ai|agent)|cognition (ai|labs).{0,20}devin"),
    ("Replit Agent", r"replit (agent|ai)"),
    ("Bolt/Lovable/v0", r"bolt\.new|stackblitz bolt|lovable (ai|dev)|vercel v0"),
    ("Warp", r"warp (terminal|agent).{0,40}(ai|agent)"),
    ("SWE-agent", r"swe-agent"),
    ("Other coding agent", r"(ai|llm)[ -]coding (agent|assistant)|coding agent"),
]
PRODUCTS = [(p, re.compile(r, re.I)) for p, r in PRODUCTS]
EXCLUDE = re.compile(r"m365 copilot|microsoft 365 copilot|copilot studio|security copilot|copilot\+ pc|dynamics 365 copilot|"
                     r"linux kernel|wordpress|pagination|opencode systems", re.I)
PACKAGES = re.compile(r"^(@anthropic-ai/claude-code|@anthropic-ai/claude-agent-sdk|claude-agent-sdk|cline|roo-cline|@openai/codex|"
                      r"@google/gemini-cli|aider-chat|openhands-ai|@qwen-code/qwen-code|opencode-ai|@continuedev/.*|kilo-code)$", re.I)


def cvss_from_vector(vector: str):
    m = re.search(r"/UI:([NRPA])", vector or "")
    return {"N": "none", "R": "required", "P": "required", "A": "required"}.get(m.group(1)) if m else ""


def classify(text: str, packages: list[str]):
    if EXCLUDE.search(text):
        return None
    for name, rx in PRODUCTS:
        if rx.search(text):
            return name
    if any(PACKAGES.search(p) for p in packages):
        return "package match"
    return None


def read_ghsa():
    root = RAW / "advisory-database" / "advisories"
    for dp, _, files in os.walk(root):
        for f in files:
            if not f.endswith(".json"):
                continue
            d = json.load(open(os.path.join(dp, f)))
            if d.get("withdrawn") or d.get("published", "") < START:
                continue
            pk = [a.get("package", {}).get("name", "") for a in d.get("affected", [])]
            s, det = d.get("summary") or "", d.get("details") or ""
            prod = classify(f"{s} {det[:600]} {' '.join(pk)}", pk)
            if not prod:
                continue
            vec = next((x.get("score", "") for x in d.get("severity", []) if "CVSS" in x.get("type", "")), "")
            yield {
                "ghsa_id": d["id"], "cve_id": next((a for a in d.get("aliases", []) if a.startswith("CVE-")), ""),
                "published": d["published"][:10], "product": prod,
                "cvss_severity": {"MODERATE": "MEDIUM"}.get(str((d.get("database_specific") or {}).get("severity")).upper(),
                                                             str((d.get("database_specific") or {}).get("severity")).upper()),
                "cvss_vector": vec, "cwe_ids": ";".join((d.get("database_specific") or {}).get("cwe_ids") or []),
                "github_reviewed": int("github-reviewed" in dp), "packages": ";".join(pk),
                "title": s, "description": det.replace("\n", " ")[:3000],
                "url": f"https://github.com/advisories/{d['id']}",
            }


def read_cve():
    root = RAW / "cvelistV5" / "cves"
    for dp, _, files in os.walk(root):
        for f in files:
            if not f.endswith(".json"):
                continue
            d = json.load(open(os.path.join(dp, f)))
            if not isinstance(d, dict):
                continue
            meta = d.get("cveMetadata", {})
            if meta.get("state") != "PUBLISHED" or meta.get("datePublished", "") < START:
                continue
            cna = d.get("containers", {}).get("cna", {})
            desc = " ".join(x.get("value", "") for x in cna.get("descriptions", []) if str(x.get("lang", "")).startswith("en"))
            aff = [f"{a.get('vendor', '')} {a.get('product', '')}" for a in cna.get("affected", []) if isinstance(a, dict)]
            prod = classify(f"{desc[:600]} {' '.join(aff)}", [])
            if not prod:
                continue
            sev, vec, score = "", "", ""
            for m in cna.get("metrics", []):
                for k in ("cvssV4_0", "cvssV3_1", "cvssV3_0"):
                    if k in m:
                        sev, vec, score = m[k].get("baseSeverity", ""), m[k].get("vectorString", ""), m[k].get("baseScore", "")
                        break
                if sev:
                    break
            cwes = [x.get("cweId", "") for p in cna.get("problemTypes", []) for x in p.get("descriptions", []) if x.get("cweId")]
            yield {
                "cve_id": meta["cveId"], "published": meta["datePublished"][:10], "product": prod,
                "cvss_severity": str(sev).upper(), "cvss_vector": vec, "cvss_score": score, "cwe_ids": ";".join(cwes),
                "title": cna.get("title", ""), "description": desc.replace("\n", " ")[:3000],
                "url": f"https://www.cve.org/CVERecord?id={meta['cveId']}",
            }


def main():
    rows = {}
    for r in read_ghsa():
        key = r["cve_id"] or r["ghsa_id"]
        rows[key] = {**r, "source": "GHSA" + (" (CVE)" if r["cve_id"] else ""), "cvss_score": ""}
    for r in read_cve():
        if r["cve_id"] in rows:  # enrich the GHSA record with CVE-list scores and CWEs
            g = rows[r["cve_id"]]
            g["cvss_score"] = g["cvss_score"] or r["cvss_score"]
            g["cvss_vector"] = g["cvss_vector"] or r["cvss_vector"]
            g["cwe_ids"] = g["cwe_ids"] or r["cwe_ids"]
            if g["cvss_severity"] in ("", "NONE"):
                g["cvss_severity"] = r["cvss_severity"]
            g["source"] = "GHSA + CVE list"
        else:
            rows[r["cve_id"]] = {**r, "ghsa_id": "", "github_reviewed": 0, "packages": "", "source": "CVE list"}
    out = sorted(rows.values(), key=lambda r: r["published"])
    for r in out:
        r["user_interaction"] = cvss_from_vector(r["cvss_vector"])
    cols = ["source", "ghsa_id", "cve_id", "published", "product", "cvss_severity", "cvss_score", "cvss_vector",
            "user_interaction", "cwe_ids", "github_reviewed", "packages", "title", "description", "url"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} unique candidate records -> {OUT}")


if __name__ == "__main__":
    main()
