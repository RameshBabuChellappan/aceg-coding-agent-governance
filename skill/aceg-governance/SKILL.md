---
name: aceg-governance
description: Assess the ethics and governance failures behind a security advisory, CVE, or incident in an AI coding agent (Claude Code, Cursor, Copilot, Codex, Cline, MCP servers, agent extensions) with the ACEG Framework, then produce a scored governance scorecard, high-impact risk estimate, triage priority, and remediation plan. Use for agent advisory triage, agent procurement reviews, and portfolio reporting.
---

# ACEG Governance Skill

Applies the **Agentic Coding Ethics and Governance (ACEG) Framework** to disclosed weaknesses in AI
coding agents and their ecosystem (extensions, MCP servers, hooks, CI workflows, bridges). The
framework, model, and review rules come from a study of all 223 public coding-agent advisories
published from 2023 to October 2026 (QM640 capstone, Walsh College).

The skill turns advisory text into five things:
1. ACEG codes: 8 domains, primary domain, 20 controls, coverage, with evidence quotes.
2. The Governance Compliance Score (GCS).
3. P(high impact): the probability that the weakness is CVSS High or Critical, predicted without using CVSS.
4. A triage priority.
5. A remediation plan mapped to the OWASP Top 10 for Agentic Applications and to NIST AI RMF functions.

## When to use

- Triage of a new advisory, CVE, or bug-bounty report for a coding agent or a component it runs.
- Pre-approval or procurement review of an agent ("which governance controls does this tool's track record show failing?").
- Portfolio reporting across many advisories (a CSV in, domain and control trends out).

Do not use it for ordinary software CVEs that involve no AI agent. ACEG controls assume an agent that reads, writes, or runs code or tools.

## Workflow

### Step 1: Collect and blind the input
Gather the title, product, component type (`agent product` or `ecosystem`), publication year,
CWE identifiers, and description. Before coding, remove the severity wording:

```bash
python scripts/mask_severity.py advisory.txt > advisory_masked.txt
```

Code from the masked text only. Severity leaks into control judgements, which is why the study kept coders blind.

### Step 2: Code the case with the codebook
Read `references/codebook.md` in full, then produce a JSON record that matches
`references/output_schema.json`:

- `domains`: every domain D1–D8 whose requirement the text shows was breached or could be breached.
- `primary_domain`: the one domain that most directly enabled the weakness. Apply the decision rules in the codebook (section 4).
- `breached_controls`: only controls linked to a present domain, and only where the text shows the control was absent, failed, or was bypassed.
- `covered`: 1 if a breached control would plausibly have prevented the weakness. Name that control in `evidence.covered_by`.
- `evidence`: one short quote from the advisory for each domain coded present.

### Step 3: Score
```bash
python scripts/aceg_score.py case.json                    # JSON scorecard to stdout
python scripts/aceg_score.py case.json --html card.html   # plus a one-page HTML scorecard
python scripts/aceg_score.py cases.csv --batch out.csv    # portfolio mode (one row per case)
```
The script uses the random-forest model in `assets/aceg_risk_model.pkl` when scikit-learn can
load it. If it cannot, it falls back automatically to the dependency-free `assets/portable_model.json`.
The output says which model was used.

### Step 4: Apply the human-review rule
In the source study, an LLM coder matched the human consensus well on **D4, D5, and D6**
(κ = .60 to .74). It was weak on **D1, D2, D3, D7, D8 and the primary domain** (κ ≤ .32). Codes in
the strong domains can be accepted after a spot check. Flag the weak domains and the primary domain
for human review, and say so in the output. Never present the scorecard as final until a person has
confirmed the flagged codes.

### Step 5: Write the remediation plan
For each breached control, take the actions in `references/controls_playbook.md` and order them as follows:
1. Priority controls first: **C01, C14, C08, C11, C02**. In the study, these carried the most predictive weight or were breached most often.
2. Then the remaining controls in the primary domain.
3. Then everything else.

Give each item an owner role (platform, security, vendor, developer) and a verification check.

## Output format

Present results in this order:
1. **Summary line**: case, product, priority tier, P(high impact) against the 70% portfolio base rate.
2. **Scorecard**: GCS (controls held / applicable), domains with family, primary domain.
3. **Breached controls**: a table of code, requirement, OWASP ASI / NIST function, and evidence quote.
4. **Remediation plan**: from the playbook, prioritized, with owner and verification.
5. **Review flags**: which codes need human confirmation (Step 4), and any coverage gap (`covered = 0` means the framework has no control for this weakness; log it for the next framework version).

Priority tiers:
- **P1**, fix before agent use: P(high) ≥ .80.
- **P2**, fix this sprint: .50 to .80.
- **P3**, routine patch cycle: below .50.

## Interpreting results correctly

- Do not use GCS alone as a risk score. In the study it did not predict severity (OR = 1.34 per SD, p = .057). Severity rose with **breadth**: each additional domain implicated more than doubled the odds of a high-impact case (OR = 2.28). Always report the number of domains and the breached controls next to GCS.
- P(high impact) is an estimate of CVSS-style technical severity. It is not a measure of exploit likelihood or business impact. On held-out cases the model reached AUC .84, and .81 when the LLM did all the coding.
- Counts by vendor reflect how much each vendor discloses. They are not safety rankings.

## Files

| File | Purpose |
|---|---|
| `references/codebook.md` | Domains, controls, coding and decision rules, worked example |
| `references/controls_playbook.md` | Remediation actions and verification checks for C01–C22 |
| `references/evidence_base.md` | Empirical priors from the 223-case study (prevalence, breach rates, drivers) |
| `references/output_schema.json` | JSON schema for a coded case |
| `scripts/mask_severity.py` | Removes CVSS and severity wording before coding |
| `scripts/aceg_score.py` | Scores a case or a CSV; writes JSON, HTML, or CSV |
| `assets/aceg_risk_model.pkl` | Random forest (ACEG + CWE features), scikit-learn ≥ 1.9 |
| `assets/portable_model.json` | Dependency-free logistic fallback with calibrated tiers |
| `assets/example_case.json` | Worked input (CA-169, a sandbox escape in Claude Code) |
