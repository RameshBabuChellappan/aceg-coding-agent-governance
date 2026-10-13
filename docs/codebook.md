# Coding Codebook — Agentic Coding Ethics and Governance (ACEG) Framework, Version 1

QM640 Data Analytics Capstone · Group 3 · Ramesh Babu Chellappan

This codebook is the ACEG framework in operational form. Human coders and the LLM pipeline (`src/03_llm_code.py`) apply exactly these definitions to every case.

## 1. Unit of analysis and eligibility

One **case** is one publicly disclosed security advisory (GitHub Advisory Database) or CVE record (CVE List V5), published from 1 January 2023 to the data freeze (11 October 2026). The record must concern an AI coding or software-engineering agent, or a component that such an agent runs.

**Include** a record when:

- it describes a weakness in an AI coding agent that can read, write or execute code, commands or tool calls (for example Claude Code, Cursor, GitHub Copilot agent features, OpenAI Codex, Gemini CLI, Cline, Roo Code, Kiro, Aider, OpenHands, OpenCode); **or**
- it describes a weakness in a component that such an agent runs or that wraps it, such as an extension, plugin, hook, MCP server, bridge, harness, CI workflow, or distribution pipeline. These are coded `component_type = ecosystem`.

**Exclude** a record when any of the following applies:

| Code | Reason |
|---|---|
| E1 | The product is not an AI coding agent or a component it runs. Examples: name collisions, browser or office assistants, tools that only mention agents. |
| E2 | The product is autocomplete-only, with no ability to act. |
| E3 | The record has too little detail to code any governance domain. |

Every exclusion is recorded with its reason in `docs/screening_decisions.csv`. A record that appears in both sources is merged on its CVE identifier.

## 2. Governance domains (code each one: 1 = present, 0 = absent)

A domain is **present** when the advisory shows that the governance requirement of that domain was breached or could be breached.

| Code | Domain | Present when the case shows… | Family |
|---|---|---|---|
| D1 | Agency and action control | The agent executed, or could be made to execute, actions beyond what was authorized, such as an approval bypass, a sandbox escape, an unauthorized command, or a destructive file operation. | A |
| D2 | Instruction and boundary adherence | Explicit user or organizational limits were not enforced, such as deny rules, ignore files, workspace or trust boundaries, or allowlists. | A |
| D3 | Transparency and honest reporting | The agent or its UI concealed or misrepresented what it would do or had done, such as hidden arguments, misleading dialogs, or false status. | D |
| D4 | Input trust and goal integrity | Untrusted content (repository files, web pages, issues, MCP or tool output, configuration) redirected the agent's goals or actions. | B |
| D5 | Secrets and data protection | Credentials, tokens, source code or personal data could be leaked, exfiltrated or exposed. | C |
| D6 | Code and supply-chain integrity | Untrusted code or configuration ran automatically, or a dependency, extension, package or build pipeline was compromised. | B |
| D7 | Accountability and recoverability | Logging, ownership, isolation of side effects, or rollback was missing, making actions hard to attribute or reverse. | D |
| D8 | Human oversight and appropriate reliance | A human checkpoint was removed or made ineffective (for example auto-approve modes, unattended CI runs), or users could not meaningfully review agent output. | A |

**Primary domain (`primary_domain`)**: the single domain that most directly enabled the weakness. Tie-break: the earliest point in the causal chain.

**Family (`domain_family`)**, used in RQ2:

- A = Agency and oversight (D1, D2, D8)
- B = Input and code integrity (D4, D6)
- C = Data protection (D5)
- D = Transparency and accountability (D3, D7)

## 3. Controls (C01–C20)

A control is **applicable** when it is linked to a domain coded as present. For each applicable control, code:

- `1` = **breached**: the advisory shows the control was absent, failed or was bypassed;
- `0` = **not breached**: the control is shown in place, or is not implicated by the advisory.

Controls linked only to absent domains are coded `NA`.

| Code | Control | Domain | Crosswalk (OWASP ASI 2026 / NIST AI RMF) |
|---|---|---|---|
| C01 | Least-privilege credentials and tool permissions | D1 | ASI02, ASI03 / MANAGE |
| C02 | Human approval gate for sensitive or irreversible actions | D1 | ASI02 / MANAGE |
| C03 | Execution isolation (sandbox; dev/prod separation) | D1 | ASI05 / MANAGE |
| C04 | Machine-enforced policy limits (deny rules, ignore files, allowlists) | D2 | ASI10 / MANAGE |
| C05 | Workspace trust and scope confirmation before execution | D2 | ASI01 / MAP |
| C06 | Faithful disclosure of planned actions (full arguments shown) | D3 | ASI09 / GOVERN |
| C07 | Tamper-evident action logs | D3 | ASI10 / GOVERN |
| C08 | Isolation and sanitization of untrusted inputs | D4 | ASI01, ASI06 / MANAGE |
| C09 | Allow-listed, integrity-checked tools and MCP servers | D4 | ASI04 / MANAGE |
| C10 | Secret scanning, redaction and protected credential storage | D5 | ASI03 / MANAGE |
| C11 | Network egress limits and data-handling policy | D5 | ASI02 / GOVERN |
| C12 | Dependency, extension and release integrity verification | D6 | ASI04 / MANAGE |
| C13 | Security testing gate before release or merge | D6 | ASI05 / MEASURE |
| C14 | No auto-execution of untrusted workspace configuration | D6 | ASI05 / MANAGE |
| C15 | Named human owner and authorization for agent actions | D7 | ASI08 / GOVERN |
| C16 | Reversible actions (checkpoints, backup and rollback) | D7 | ASI08 / MANAGE |
| C17 | Incident response, patching and disclosure process | D7 | ASI08 / MANAGE |
| C18 | Autonomy level matched to risk (safe defaults for auto modes) | D8 | ASI09 / MAP |
| C19 | Human review of agent-authored changes and commands | D8 | ASI09 / MANAGE |
| C20 | Capability and limitation disclosure to users | D8 | ASI09 / GOVERN |

## 4. Derived scores

- `n_domains` = number of domains present (0–8).
- `n_applicable` = number of applicable controls.
- `n_breached` = number of applicable controls coded 1.
- **Governance Compliance Score**: `gcs = 100 × (n_applicable − n_breached) / n_applicable`. This is the share of the framework controls relevant to the case that held.
- **Framework coverage** (`covered`): 1 if at least one domain is present **and** at least one breached control would, if in place, plausibly have prevented the weakness; otherwise 0. A case with `covered = 0` is a framework gap and is logged for version 2.

## 5. Variables taken directly from the source (not coded)

- `cvss_severity` and `cvss_score`: as published, CVSS v4.0 preferred, otherwise v3.x.
- `high_impact` = 1 if `cvss_severity` is HIGH or CRITICAL (CVSS ≥ 7.0); otherwise 0. This is the RQ3 outcome.
- `user_interaction_required`: from the CVSS vector (`UI:N` = 0; `UI:R`, `UI:P` or `UI:A` = 1). This is the RQ2 grouping variable.
- `component_type`: agent product or ecosystem component, assigned at screening.

These CVSS-derived fields are **hidden from coders and from the LLM pipeline** (blinding), so control judgments cannot be influenced by the outcome. They are merged back only by `src/06_build_coded_dataset.py`. The CVSS figures in the worked example below are shown for illustration only; coders do not see them for real cases.
- `cwe_ids`, `published`, `year`, `product`.

## 6. Procedure

1. **Pilot.** Both coders code the same 20 cases. Compute Cohen's κ per domain. Revise the wording of any domain with κ < 0.60, and record the change in `framework_changelog.md`.
2. **Main coding.** Both coders code all cases independently. Disagreements are resolved by discussion, and the agreed label becomes the gold label.
3. **LLM pipeline.** The pipeline codes the same cases without seeing the gold labels.
4. **Anonymity.** Reporter names in advisories are not copied into the coded dataset.

## 7. Worked example — CA-018 (CVE-2025-54795, GHSA-x56v-x2h6-7j34)

**Advisory.** A command-parsing error let untrusted content in Claude Code's context bypass the confirmation prompt and execute a command. CVSS 4.0 score is 8.7 (HIGH), with `UI:P`.

**Domains present.**

- D1: a command was executed without approval.
- D4: the trigger was untrusted content in the context window.

**Primary domain.** D1 (family A).

**Controls.** Five are applicable:

- breached (1): C02 (approval gate bypassed) and C08 (untrusted input not isolated);
- not breached (0): C01, C03 and C09.

**Scores.**

- GCS = 100 × (5 − 2) / 5 = **60.0%**
- covered = 1, because a working C02 would have blocked the command
- high_impact = 1; user_interaction_required = 1
