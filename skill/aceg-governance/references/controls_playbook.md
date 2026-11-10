# ACEG Controls Playbook: remediation actions and verification checks

Owners: **P** = platform or DevEx team · **S** = security or AI-governance team · **V** = agent vendor (raise a ticket, pin a fixed version) · **D** = developer practice.
Priority controls, from the evidence base: **C01, C14, C08, C11, C02**.

| Control | Remediation actions | Owner | Verification check |
|---|---|---|---|
| C01 Least privilege | Run agents under scoped, short-lived credentials. Do not mount cloud or admin tokens in agent sessions. Give CI agents read-only `GITHUB_TOKEN` unless a write is needed. | P, S | Inventory the credentials visible to an agent session; none should exceed the task's scope |
| C02 Approval gate | Require approval for shell, network, and write-outside-workspace actions. Turn off auto-approve for commands that change the system. Pin a vendor version that fixes the parser bypass. | P, V | A red-team prompt cannot run `curl`, `rm`, or `git push` without a prompt |
| C03 Execution isolation | Run agents in a container, VM, or OS sandbox. Keep production credentials and networks out of developer sandboxes. | P | A sandbox escape test (symlinks, Git hooks, Docker socket) fails |
| C04 Policy limits | Enforce deny rules and allowlists in a managed policy that canonicalizes paths and parses commands. Fail closed on commands the parser does not recognize. | P, V | Regression tests on symlink, case-variant, and shell-substitution bypasses pass |
| C05 Workspace trust | Require explicit trust before loading project settings, `.env`, hooks, or MCP definitions, including in headless and CI modes. | P, V | Opening an untrusted repository runs nothing before a trust decision |
| C06 Faithful disclosure | Show full commands and arguments in approval dialogs and MCP install prompts. Make documentation of safety features accurate. | V | The approval UI shows the full argument string; documentation matches behaviour |
| C07 Action logs | Write tamper-evident logs of agent tool calls, commands, and file writes, and send them to the security information and event management (SIEM) system. | P, S | You can reconstruct every action of a session from the logs |
| C08 Untrusted-input isolation | Treat repository files, web content, issue text, tool and MCP output, and file names as untrusted. Delimit and neutralize them. Never interpolate them into shell strings; use argument arrays. | V, D | Prompt-injection and command-injection test suites run against the agent configuration |
| C09 Tool and MCP allowlist | Allow-list MCP servers and extensions by publisher and hash. Re-approve whenever a definition changes. Block servers that come from the repository. | P, S | A changed MCP definition triggers re-approval; unlisted servers are blocked |
| C10 Secret protection | Keep secrets out of agent context and logs. Use a secret manager. Store token files at 0600. Redact secrets from transcripts. | P, S | A secret scan of agent transcripts and caches finds nothing |
| C11 Egress limits | Restrict agent network egress to allow-listed domains (exact host, not prefix). Disable automatic remote image rendering and schema fetching. | P | A canary exfiltration test to an unlisted domain is blocked |
| C12 Release integrity | Verify signatures and provenance of agent binaries, extensions, and packages (OIDC provenance, pinned hashes). | P, V | Every installed agent artefact has verified provenance |
| C13 Security testing gate | Add security tests (injection, traversal, sandbox) to the release gate for agent tools and internal agent integrations. | V, S | The release checklist includes passing agent security tests |
| C14 No auto-execution of config | Disable automatic execution of workspace tasks, Git hooks, `fsmonitor`, `.env` routing keys, and build wrappers when an agent opens a repository. | P, V | Opening a booby-trapped repository runs nothing |
| C15 Named owner | Assign a named human owner and authorization scope to each agent deployment and to each approval channel. | S | Every agent deployment has an owner in the inventory |
| C16 Reversible actions | Turn on checkpoints and backups. Block destructive operations on production data; require a code freeze to be machine-enforced. | P | A restore drill succeeds; destructive commands are blocked in production |
| C17 Incident response | Track vendor advisories. Set patch service-level agreements for agent tools. Replace unsupported or unresponsive tools. | S | All agent tools are on supported, patched versions |
| C18 Autonomy matched to risk | Make safe defaults mandatory. Allow auto, "yolo", or bypass modes only in disposable sandboxes. Never run unattended agents on untrusted input. | P, S | Policy scan shows no bypass modes outside sandboxes |
| C19 Human review | Require human review of agent-authored diffs and commands before merge or execution in shared environments. | D, S | Branch protection requires a human reviewer on agent pull requests |
| C20 Capability disclosure | Document what the agent can access and do, and its limits, for every user group. | V, S | Users can name the agent's permissions in onboarding checks |
| C21* Local endpoint security | Bind agent servers to localhost with authentication tokens and Origin checks; no wildcard CORS. | V | A cross-origin WebSocket or HTTP request from a browser is rejected |
| C22* Transport verification | Verify SSH host keys and TLS certificates for remote agent sessions. | V, P | A man-in-the-middle test with a spoofed host key fails |

*Version 2 extension controls (not part of the GCS).
