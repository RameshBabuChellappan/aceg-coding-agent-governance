# ACEG Codebook (Version 1 scoring set, with Version 2 decision rules)

## 1. Unit and scope
One case is one advisory, CVE record, bug report, or incident about an AI coding agent (an agent that reads, writes, or runs code, commands, or tool calls) or about a component the agent runs (extension, plugin, hook, MCP server, bridge, harness, CI workflow, distribution pipeline). Set `component_type = "ecosystem"` for components. Autocomplete-only tools and products that are not agents are out of scope.

## 2. Domains (code 1 = present, 0 = absent)
A domain is **present** when the text shows that the domain's governance requirement was breached or could be breached.

| Code | Domain | Present when the case shows... | Family | Controls |
|---|---|---|---|---|
| D1 | Agency and action control | The agent executed, or could be made to execute, actions beyond what was authorized: approval bypass, sandbox escape, an unauthorized command, a destructive file operation, an unauthenticated endpoint that runs commands | A | C01–C03 |
| D2 | Instruction and boundary adherence | An explicit user or organizational limit was not enforced: deny rules, ignore files, allowlists, workspace or path boundaries, managed policy | A | C04–C05 |
| D3 | Transparency and honest reporting | The agent, its UI, or its documentation concealed or misrepresented what it would do or had done: hidden arguments, misleading dialogs, false safety claims | D | C06–C07 |
| D4 | Input trust and goal integrity | Untrusted content (repository files, web pages, issues, MCP or tool output, file names, configuration) redirected the agent's goals or actions, or was injected into commands | B | C08–C09 |
| D5 | Secrets and data protection | Credentials, tokens, source code, conversation history, or personal data could be leaked, exfiltrated, or exposed | C | C10–C11 |
| D6 | Code and supply-chain integrity | Untrusted code or configuration ran automatically, or a dependency, extension, package, release, or build pipeline was compromised | B | C12–C14 |
| D7 | Accountability and recoverability | Ownership or authorization of actions, rollback, or incident response was missing: irreversible actions, the wrong person able to approve, the vendor not responding or not patching | D | C15–C17 |
| D8 | Human oversight and appropriate reliance | A human checkpoint was removed or made ineffective (auto-approve or "yolo" modes, unattended CI runs, insecure defaults), or users could not meaningfully review agent output | A | C18–C20 |

Families: A = Agency and oversight; B = Input and code integrity; C = Data protection; D = Transparency and accountability.

## 3. Controls (code only those linked to a present domain)
1 = breached (absent, failed, or bypassed according to the text); 0 = held or not implicated.

| Code | Control | Domain | OWASP ASI / NIST AI RMF |
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
| C10 | Secret scanning, redaction, and protected credential storage | D5 | ASI03 / MANAGE |
| C11 | Network egress limits and data-handling policy | D5 | ASI02 / GOVERN |
| C12 | Dependency, extension, and release integrity verification | D6 | ASI04 / MANAGE |
| C13 | Security testing gate before release or merge | D6 | ASI05 / MEASURE |
| C14 | No auto-execution of untrusted workspace configuration | D6 | ASI05 / MANAGE |
| C15 | Named human owner and authorization for agent actions | D7 | ASI08 / GOVERN |
| C16 | Reversible actions (checkpoints, backup, rollback) | D7 | ASI08 / MANAGE |
| C17 | Incident response, patching, and disclosure process | D7 | ASI08 / MANAGE |
| C18 | Autonomy level matched to risk (safe defaults for auto modes) | D8 | ASI09 / MAP |
| C19 | Human review of agent-authored changes and commands | D8 | ASI09 / MANAGE |
| C20 | Capability and limitation disclosure to users | D8 | ASI09 / GOVERN |

**Version 2 extension controls.** Record these in `extension_controls`. They are reported, but they are not part of the GCS or the model.
- **C21: Authenticated, origin-checked local agent endpoints.** Applies to HTTP and WebSocket servers started by agents or their tools.
- **C22: Transport and host verification for remote agent sessions.** Covers SSH host keys and TLS checks.

## 4. Decision rules (Version 2; these address the low-agreement areas found in the study)
1. **D1 or D2.** If a configured limit was bypassed (allowlist, deny rule, ignore file, path or workspace boundary), code D2 and make it the primary domain. If an action ran without the approval it needed, code D1. Code both only when the text states both.
2. **Command injection.** Unsanitized input reaching a shell is D4 (C08). Add D1 (C02) only when the agent itself runs the command without approval.
3. **Repository configuration that runs on open or start-up** (hooks, `.env`, settings, MCP definitions, Git config): code D6 (C14). Add D2 (C05) when the trust dialog was bypassed or never shown.
4. **D3** only when the text says something was hidden or misrepresented (dialog, UI, documentation). Do not code it for an ordinary bug.
5. **D7** only when the text shows missing ownership or authorization of actions (C15), irreversible damage (C16), or a vendor that did not respond or patch (C17).
6. **D8** when an auto-approve, "yolo", headless, or unattended mode, or an insecure default, removed the human checkpoint.
7. **Primary domain.** Choose the domain that most directly enabled the weakness. Break ties by the earliest point in the causal chain, in this order: D4, D6, D2, D1, D8, D5, D3, D7.
8. **Thin records.** For one-line CVE text, code only what is stated and set `confidence = "low"`.

## 5. Derived scores
- `n_domains` = number of domains present.
- `n_applicable` = number of controls linked to present domains.
- `n_breached` = number of those controls coded 1.
- **GCS** = 100 × (n_applicable − n_breached) / n_applicable.

## 6. Worked example: CA-018 (approval-prompt bypass in Claude Code)
- **Text:** a command-parsing error let untrusted content in the context window bypass the confirmation prompt and run a command.
- **Domains:** D1 (a command ran without approval) and D4 (the trigger was untrusted content). Primary domain D1.
- **Controls:** C02 and C08 breached; C01, C03, and C09 held.
- **Scores:** GCS = 100 × (5 − 2) / 5 = 60.0%. covered = 1, because a working C02 would have blocked the command.
