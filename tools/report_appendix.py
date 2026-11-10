# Appendices (executed by build_report.py after report_content.py)
dd = pd.read_csv(ROOT / "docs/data_dictionary.csv")
num = pd.read_csv(T / "eda_numeric_summary.csv", index_col=0)
clog = pd.read_csv(T / "cleaning_log_coding.csv")
rq2s = pd.read_csv(T / "rq2_by_source.csv")

# ---------------- Appendix A
H1("Appendix A", page_break=True)
H1("Data Dictionary")
P("Table A1 defines the source and coded variables used in the analysis (docs/data_dictionary.csv in the repository). The same 30 coded fields (d1 to d8, primary_domain, c01 to c20, covered) are stored for Coder 1, Coder 2, the LLM coder, and the final labels in the four codes_* tables of data/aceg.db.")
handling = {"cvss_score": "31 missing: 24 recomputed from v3.x vector; 7 left missing", "cvss_vector": "2 missing; excluded from RQ2 only",
            "user_interaction_required": "2 missing; excluded from RQ2 only", "cve_id": "4 structurally missing (GitHub-only)",
            "ghsa_id": "77 structurally missing (CVE-only)", "c01 to c20": "NA when the control's domain is absent",
            "gcs": "Defined for all 223 cases in final labels", "domain_family": "From final primary domain"}
rows = []
skip = {"coder1_primary_domain", "coder2_primary_domain", "gold_primary_domain"}
for _, r in dd.iterrows():
    if r.variable in skip:
        continue
    rows.append([r.variable, r.type, r.meaning, r.units_or_values, handling.get(r.variable, "None missing"), r.relevance])
TABLE("A1", "Data Dictionary of Source and Coded Variables",
      ["Variable", "Type", "Definition", "Allowed values / units", "Missing-value handling", "Role"], rows,
      [1.25, 0.7, 1.35, 1.05, 1.05, 0.95], size=8,
      notes="Variables prefixed llm_ hold the LLM coder's labels; the human coders' labels are stored in codes_coder1 and codes_coder2 with the same names. title was missing for 82 CVE-only records and was filled with the first 120 characters of the description.")

# ---------------- Appendix B
H1("Appendix B", page_break=True)
H1("ACEG Framework: Version 1 Controls and Evidence-Based Version 2 Changes")
P("Table B1 lists the ACEG Version 1 domains, families, and controls with their crosswalk to the OWASP agentic risk codes (ASI) and NIST AI RMF functions, together with the number of cases in which each control was applicable and breached under the final labels. Table B2 records the changes proposed for Version 2 and the evidence behind each change (docs/framework_changelog.md).")
cmap = {1: ("D1 Agency and action control (A)", "Least-privilege credentials and tool permissions", "ASI02, ASI03 / MANAGE"),
        2: ("", "Human approval gate for sensitive or irreversible actions", "ASI02 / MANAGE"),
        3: ("", "Execution isolation (sandbox; dev/prod separation)", "ASI05 / MANAGE"),
        4: ("D2 Instruction and boundary adherence (A)", "Machine-enforced policy limits (deny rules, ignore files, allowlists)", "ASI10 / MANAGE"),
        5: ("", "Workspace trust and scope confirmation before execution", "ASI01 / MAP"),
        6: ("D3 Transparency and honest reporting (D)", "Faithful disclosure of planned actions", "ASI09 / GOVERN"),
        7: ("", "Tamper-evident action logs", "ASI10 / GOVERN"),
        8: ("D4 Input trust and goal integrity (B)", "Isolation and sanitization of untrusted inputs", "ASI01, ASI06 / MANAGE"),
        9: ("", "Allow-listed, integrity-checked tools and MCP servers", "ASI04 / MANAGE"),
        10: ("D5 Secrets and data protection (C)", "Secret scanning, redaction, protected credential storage", "ASI03 / MANAGE"),
        11: ("", "Network egress limits and data-handling policy", "ASI02 / GOVERN"),
        12: ("D6 Code and supply-chain integrity (B)", "Dependency, extension, and release integrity verification", "ASI04 / MANAGE"),
        13: ("", "Security testing gate before release or merge", "ASI05 / MEASURE"),
        14: ("", "No auto-execution of untrusted workspace configuration", "ASI05 / MANAGE"),
        15: ("D7 Accountability and recoverability (D)", "Named human owner and authorization for agent actions", "ASI08 / GOVERN"),
        16: ("", "Reversible actions (checkpoints, backup, rollback)", "ASI08 / MANAGE"),
        17: ("", "Incident response, patching, and disclosure process", "ASI08 / MANAGE"),
        18: ("D8 Human oversight and reliance (A)", "Autonomy level matched to risk (safe defaults)", "ASI09 / MAP"),
        19: ("", "Human review of agent-authored changes and commands", "ASI09 / MANAGE"),
        20: ("", "Capability and limitation disclosure to users", "ASI09 / GOVERN")}
rows = []
for c in range(1, 21):
    r = ctrl.iloc[c - 1]
    rows.append([cmap[c][0], f"C{c:02d}", cmap[c][1], cmap[c][2], int(r.applicable), f"{int(r.breached)} ({100*r.breach_rate_applicable:.0f}%)" if r.applicable else "0"])
TABLE("B1", "ACEG Version 1 Domains, Controls, Crosswalk, and Breach Frequency (Final Labels)",
      ["Domain (family)", "Code", "Control", "OWASP ASI / NIST AI RMF", "Applicable n", "Breached n (%)"], rows,
      [1.45, 0.45, 2.1, 1.1, 0.65, 0.75], size=8,
      notes="GCS = 100 × (applicable − breached) / applicable. Families: A agency and oversight; B input and code integrity; C data protection; D transparency and accountability.")
V2 = [
    ["Merge D3 and D7 into one domain, Transparency and accountability, with explicit triggers (UI hides arguments; documentation misstates a safety property; vendor did not respond or patch)",
     "Human–human κ = .00 for D3 and D7; Coder 1 coded D3 in 57.8% of cases, Coder 2 in 0%; final prevalence 2.7% and 1.3%", "RQ4, RQ1"],
    ["Decision rule separating D1 and D2: bypass of a configured limit (allowlist, deny rule, ignore file, path boundary) is D2 and primary; an action run without approval is D1; code both only when both are stated",
     "κ = .16 (D1) and .22 (D2); LLM over-coded D2 in 44 consensus-negative cases; primary-domain κ = .22", "RQ4"],
    ["Coverage must name the preventing control (evidence field)", "Coder 1 coded covered = 1 for every case (no variance; κ undefined)", "RQ1, RQ4"],
    ["Add C21 Authenticated, origin-checked local agent endpoints (HTTP/WebSocket)", "15 cases expose agent servers without authentication or origin checks (for example CA-070, CA-117, CA-214)", "RQ1"],
    ["Add C22 Transport and host verification for remote agent sessions", "Only uncovered case (CA-121, SSH host-key check)", "RQ1"],
    ["Keep C01, C08, C11, C14 as priority controls in the scorecard", "Top permutation-importance controls in the best model (Figure 6)", "RQ3"],
    ["Review C07, C16, C20 (never breached) and C13, C15, C17 (rarely breached) for merging", "0 to 2 breaches each under final labels (Table B1)", "RQ1, RQ3"],
    ["Report GCS together with number of domains and breached controls, never alone", "GCS OR unstable across label sources; n_domains OR = 2.28", "RQ3"],
]
TABLE("B2", "Proposed ACEG Version 2 Changes and Supporting Evidence", ["Change", "Evidence", "Source RQ"], V2, [3.0, 2.6, 0.7], size=8.5)

# ---------------- Appendix C
H1("Appendix C", page_break=True)
H1("Data Cleaning and Additional Exploratory Analysis")
P("Table C1 summarizes the cleaning actions, Table C2 gives descriptive statistics of the numeric variables, and Figure C1 shows the distribution of CVSS base scores and the cases by product.")
CL = [
    ["Missing values", "cvss_score (31; 13.9%)", "isna() count", f"{C['recovered']} recomputed from v3.x vectors (all {C['recovered_band_match']} match the published band); {C['left_missing']} left missing", "Deterministic recovery; outcome complete"],
    ["Missing values", "title (82; 36.8%)", "isna() count", "Filled with first 120 characters of description", "Text retained for coders"],
    ["Missing values", "cvss_vector, user_interaction (2)", "isna() count", "Excluded from RQ2 only (n = 221)", "Listwise deletion limited to the analysis needing the field"],
    ["Duplicates", "All rows; cve_id; ghsa_id", "duplicated()", "0 exact duplicates; cross-source records merged on CVE at screening", "One case per vulnerability"],
    ["Outliers", "cvss_score (3 below 3.2)", "Tukey fences (Q1 = 6.5, Q3 = 8.7)", "Kept", "Valid Low ratings"],
    ["Outliers", "description length (26)", "Tukey upper fence", "Kept; log scale in EDA only", "Long advisories are informative"],
    ["Inconsistency", f"score vs. vector ({C['score_vector_mismatch']} of {C['v3_with_score']} v3.x)", "Score recomputed from vector", f"Published severity kept; band differs in {C['band_flip']}, outcome in {C['outcome_flip']}", "Scorer differences documented"],
    ["Coding rule breach", f"Coder 1 control cells ({len(clog)})", "Rule check vs. domain codes", "Reset to NA; logged (outputs/final/tables/cleaning_log_coding.csv)", "Codebook rule 4"],
]
TABLE("C1", "Data Cleaning Log", ["Issue", "Variables affected", "Detection", "Treatment", "Rationale"], CL, [0.95, 1.3, 1.1, 1.85, 1.2], size=8.5)
rows = []
for idx, r in num.iterrows():
    rows.append([idx, int(r["count"]), f"{r['mean']:.2f}", f"{r['std']:.2f}", f"{r['min']:.1f}", f"{r['25%']:.1f}", f"{r['50%']:.1f}", f"{r['75%']:.1f}", f"{r['max']:.1f}", f"{r['skew']:.2f}"])
TABLE("C2", "Descriptive Statistics of Numeric Variables", ["Variable", "n", "M", "SD", "Min", "Q1", "Mdn", "Q3", "Max", "Skew"], rows,
      [1.9, 0.4, 0.5, 0.5, 0.45, 0.45, 0.45, 0.45, 0.5, 0.45], size=8.5,
      notes="M = mean; Mdn = median; Q1 and Q3 = quartiles. CVSS score after recovery from vectors (7 still missing).")
FIGURE("C1", "Distribution of CVSS Base Scores and Cases by Product", FIG / "fig_eda_cvss_product.png", 6.2,
       "Panel (a): bins of 0.5 points, n = 216; dashed line marks the High threshold. Panel (b): the ten products with the most cases, split by impact class.")

# ---------------- Appendix D
H1("Appendix D", page_break=True)
H1("Additional Results and Robustness Checks")
P("Table D1 and Figure D1 report the RQ3 sensitivity analyses; Table D2 the full-data cross-validation of all models; Table D3 the pairwise and three-rater agreement for every coded item; Table D4 the RQ2 test under each coder's labels; Figure D2 the RQ2 cross-tabulation; and Figure D3 the LLM coder's precision, recall, and κ against the human consensus.")
rows = [[r.Specification, int(r.n), f"{r.OR:.2f}", f"[{r.lo:.2f}, {r.hi:.2f}]", pval(r.p).replace("= ", ""), nz(r.McFadden, 3)] for _, r in sens.iterrows()]
TABLE("D1", "Sensitivity Analyses for the RQ3 Hypothesis Model", ["Specification", "n", "OR per SD", "95% CI", "p", "McFadden R²"], rows,
      [3.0, 0.4, 0.7, 0.95, 0.55, 0.75], size=9,
      notes="All models adjust for ecosystem component, number of domains (from the same label source), and publication in 2026.")
FIGURE("D1", "Odds Ratio for GCS Across Sensitivity Specifications", FIG / "fig_rq3_sensitivity.png", 5.6,
       "Points are odds ratios per SD; lines are 95% CIs; the dashed line marks OR = 1 (log scale).")
rows = [[r.Model, f"{nz(r.auc,3)} ({nz(r.auc_sd,3)})", f"{nz(r.bal_acc,3)} ({nz(r.bal_acc_sd,3)})"] for _, r in cvf.iterrows()]
TABLE("D2", "Full-Data Repeated Cross-Validation (5 Folds × 10 Repeats, N = 223)", ["Model", "AUC M (SD)", "Balanced accuracy M (SD)"], rows, [3.4, 1.4, 1.6], size=9,
      notes="Hyperparameters as tuned on the training split. Each model is refitted within each of the 50 folds.")
rows = []
for _, r in pairs.iterrows():
    fmt = lambda v: "n/a" if pd.isna(v) else nz(v)
    pct = lambda v: "—" if pd.isna(v) else f"{v:.1f}"
    rows.append([r.Item, pct(r.C1_pct), pct(r.C2_pct), pct(r.LLM_pct), fmt(r.k_C1_C2), fmt(r.k_C1_LLM), fmt(r.k_C2_LLM), fmt(r.fleiss)])
rows.append(["Pooled domains", "", "", "", nz(R4['hh_pooled_kappa']), nz(R4['c1_llm_pooled']), nz(R4['c2_llm_pooled']), nz(R4['fleiss_pooled'])])
TABLE("D3", "Prevalence and Pairwise Agreement by Coder", ["Item", "Coder 1 %", "Coder 2 %", "LLM %", "κ C1–C2", "κ C1–LLM", "κ C2–LLM", "Fleiss κ"], rows,
      [1.4, 0.7, 0.7, 0.6, 0.7, 0.7, 0.7, 0.7], size=9,
      notes="κ is 0 or undefined where one coder never used a category (Coder 2 never coded D3 or D7; Coder 1 coded every case as covered).")
rows = [[{"coder1": "Coder 1", "coder2": "Coder 2", "llm": "LLM coder"}[r.labels], f"{r.chi2:.2f}", int(r.df), nz(r.p, 3), nz(r.V)] for _, r in rq2s.iterrows()]
rows.insert(0, ["Final labels", f"{R2['chi2']:.2f}", R2['df'], nz(R2['p'], 3), nz(R2['V'])])
TABLE("D4", "RQ2 Chi-Square Test Under Each Label Source", ["Labels", "χ²", "df", "p", "Cramér's V"], rows, [2.0, 0.8, 0.5, 0.7, 0.9], size=9,
      notes="Coder 2 used only three families as primary domains (df = 2).")
FIGURE("D2", "Domain Family of the Primary Domain by Need for User Interaction (RQ2)", FIG / "fig_rq2_family_ui.png", 5.6,
       "n = 221 cases with a CVSS vector. Labels on the bars give the share requiring interaction.")
FIGURE("D3", "LLM Coder Against the Human Consensus by Domain (RQ4)", FIG / "fig_rq4_llm_consensus.png", 6.0,
       "n = cases on which both human coders agreed. D3 and D7 have no consensus-positive cases, so precision, recall, and κ are undefined.")

# ---------------- Appendix E
H1("Appendix E", page_break=True)
H1("Reproduction Steps, Database Queries, and API Example")
P("All results are reproduced from the public repository with the steps below (Python 3.13; about 5 minutes on a 2-core CPU; seed 42). The code used to generate every table and figure is in src/ and tools/; for example, src/09_final_analysis.py generates Figures 1, 2, and 4 to 9, and tools/architecture_diagram.py generates Figure 3.")
STEPS = [
    "pip install -r requirements.txt; python sample_size/sample_size.py (Table 4).",
    "Clone the two sources at the commits in docs/data_freeze.md; python src/01_collect.py (239 records); python src/02_screen.py (223 cases).",
    "python src/07_parse_llm_codes.py (expands data/llm/llm_codes_compact.txt to data/processed/llm_codes.csv).",
    "python src/08_build_gold_and_db.py (reads coding/completed/*.xlsx, cleans, builds majority labels, writes data/processed/cases_coded.csv and data/aceg.db).",
    "python src/09_final_analysis.py (RQ1 to RQ4, models M0 to M7, tables in outputs/final/tables/, figures in outputs/final/figures/, summary.json, models/*.pkl).",
    "python src/10_scorecard_service.py serve (REST API on port 8080) or python src/10_scorecard_service.py demo CA-169 (HTML scorecard).",
    "python src/11_build_skill_and_evaluate.py (portable model, skill assets, end-to-end skill evaluation in outputs/final/tables/skill_evaluation.csv).",
    "Skill use: python skill/aceg-governance/scripts/aceg_score.py skill/aceg-governance/assets/example_case.json --html card.html (single case) or ... example_batch_llm_coded.csv --batch scored.csv (portfolio).",
    "python tools/architecture_diagram.py; python tools/skill_diagram.py; python tools/build_report.py (this report).",
]
for i, s_ in enumerate(STEPS, 1):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.5); p.paragraph_format.first_line_indent = Inches(-0.25)
    runs(p, f"{i}. {s_}")
P("*Example SQL query (data access).* The analysis view joins source records and final labels:", indent=False)
CODE = ["SELECT c.case_id, c.product, c.high_impact,",
        "       g.gcs, g.n_domains, g.primary_domain",
        "FROM cases AS c JOIN codes_gold AS g USING (case_id)",
        "WHERE c.component_type = 'agent product' AND g.d1 = 1",
        "ORDER BY g.gcs;"]
for line in CODE:
    p = doc.add_paragraph(); p.paragraph_format.line_spacing = 1.0; p.paragraph_format.left_indent = Inches(0.3); p.paragraph_format.first_line_indent = Inches(0)
    rr = p.add_run(line); rr.font.name = "Courier New"; rr.font.size = Pt(9)
doc.add_paragraph().paragraph_format.line_spacing = 1.0
P("*Example API call (deployment).* A coded advisory is posted to the scorecard service, which returns the scorecard as JSON:", indent=False)
CODE = ['curl -X POST http://127.0.0.1:8080/score \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"case_id": "NEW-001", "component_type": "agent product",',
        '       "year": 2026, "cwe_ids": "CWE-78", "domains": [1, 2, 4],',
        '       "primary_domain": 2, "breached_controls": [2, 4, 8]}\'',
        'Response: {"gcs": 57.1, "n_domains": 3, "p_high_impact": 0.919,',
        '  "risk_tier": "Priority 1: fix before agent use",',
        '  "breached_controls": [{"code": "C02", ...}, {"code": "C04", ...},',
        '                        {"code": "C08", ...}], ...}']
for line in CODE:
    p = doc.add_paragraph(); p.paragraph_format.line_spacing = 1.0; p.paragraph_format.left_indent = Inches(0.3); p.paragraph_format.first_line_indent = Inches(0)
    rr = p.add_run(line); rr.font.name = "Courier New"; rr.font.size = Pt(8.5)
doc.add_paragraph().paragraph_format.line_spacing = 1.0

# ---------------- Appendix F
H1("Appendix F", page_break=True)
H1("ACEG Governance Skill: Instructions, Package, and Example Run")
P("The ACEG Governance Skill is the industry deliverable of the project (skill/aceg-governance/ in the repository; Table 11 lists its files). It packages the codebook, the blinding rule, the trained models, the human-review rule from RQ4, and the remediation playbook so that any LLM agent can apply the framework to a new advisory. Its SKILL.md is summarized below. The LLM coder used in RQ4 followed the same coding instructions (Steps 1 and 2).")
SK = [
    "Name and trigger: aceg-governance. Use it when assessing a security advisory, CVE, or incident in an AI coding agent or its ecosystem (extensions, MCP servers, hooks, CI workflows) to produce a governance scorecard, high-impact risk estimate, triage priority, and remediation plan. Do not use it for software CVEs that involve no agent.",
    "Step 1, collect and blind: gather the title, product, component type, year, CWE identifiers, and description; run scripts/mask_severity.py and code only from the masked text.",
    "Step 2, code: read references/codebook.md; mark each domain D1 to D8 present if its requirement was breached or could be breached; choose one primary domain using the Version 2 decision rules; list breached controls of present domains only; set covered and name the preventing control; quote evidence; return JSON that matches references/output_schema.json.",
    "Step 3, score: run scripts/aceg_score.py case.json (or a CSV with --batch). It reports the GCS, the number of domains, the family, P(high impact) against the 70% base rate, the priority tier (P1 at .80 or above, P2 from .50, P3 below .50), and the model used (random forest or portable fallback).",
    "Step 4, human review: accept D4, D5, and D6 after spot checks; flag D1, D2, D3, D7, D8, and the primary domain for confirmation; never present the scorecard as final until a person has confirmed the flagged codes.",
    "Step 5, remediate and report: for each breached control, take the actions, owner, and verification check from references/controls_playbook.md; list the priority controls C01, C14, C08, C11, and C02 first; log any coverage gap for the next framework version.",
    "Interpretation rules: never use GCS alone as a risk score (always report it with the number of domains and the breached controls); P(high impact) estimates CVSS-style technical severity, not exploit likelihood or business impact; advisory counts by vendor are not safety rankings.",
]
for s_ in SK:
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.5); p.paragraph_format.first_line_indent = Inches(-0.25)
    runs(p, "– " + s_)
P("*Example run (CA-169, single-case mode).* The command and an abridged output follow:", indent=False)
CODE = ["$ python scripts/aceg_score.py assets/example_case.json --html card.html",
        '{"case_id": "CA-169", "gcs": 60.0, "controls_held": 6, "n_applicable": 10,',
        ' "n_domains": 4, "primary_domain": "D4 Input trust and goal integrity",',
        ' "p_high_impact": 0.873, "priority": "P1 fix before agent use",',
        ' "remediation_plan": [{"control": "C14", "action": "Disable hooks, tasks,',
        '    fsmonitor and .env routing on repository open", ...},',
        '   {"control": "C08", ...}, {"control": "C03", ...}, {"control": "C04", ...}],',
        ' "human_review_required": ["D1", "D2", "primary_domain"],',
        ' "model_used": "M7 Random forest: ACEG + CWE"}',
        "$ python scripts/aceg_score.py assets/example_batch_llm_coded.csv --batch scored.csv",
        '{"cases": 223, "priority_counts": {"P1 fix before agent use": 63,',
        '  "P2 fix this sprint": 96, "P3 routine patch cycle": 64}, "model_used": "forest"}']
for line in CODE:
    p = doc.add_paragraph(); p.paragraph_format.line_spacing = 1.0; p.paragraph_format.left_indent = Inches(0.3); p.paragraph_format.first_line_indent = Inches(0)
    rr = p.add_run(line); rr.font.name = "Courier New"; rr.font.size = Pt(8.5)
doc.add_paragraph().paragraph_format.line_spacing = 1.0
P("The single-case output uses the random forest refitted on all 223 cases, which is the production model, so CA-169's probability (.873) differs slightly from the out-of-sample value in Figure 11 (.86, from the hold-out model). The portfolio counts come from fully automated LLM coding of all 223 cases.", indent=True)
