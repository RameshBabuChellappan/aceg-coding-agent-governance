# Evidence base: 223 public coding-agent advisories (Oct 2023 to Oct 2026)

These priors come from the capstone study. Use them to put a new case in context.

## Data and labels
- Sources: GitHub Advisory Database and CVE List V5, frozen 11 October 2026.
- 223 cases across 20 products: Claude Code 58, Cursor 32, GitHub Copilot 24, others 109.
- 70% of cases are High or Critical.
- Labels: majority vote of two human coders and a blinded LLM coder.

## Domain prevalence
| Domain | Prevalence |
|---|---|
| D1 Agency and action control | 66.8% |
| D4 Input trust and goal integrity | 51.6% |
| D2 Instruction and boundary adherence | 35.4% |
| D5 Secrets and data protection | 30.0% |
| D6 Code and supply-chain integrity | 24.7% |
| D8 Human oversight and reliance | 9.9% |
| D3 Transparency and honest reporting | 2.7% |
| D7 Accountability and recoverability | 1.3% |

The most common chain is untrusted input, then an approval or allowlist bypass, then command execution (D1 with D4 in 74 cases).

## Most-breached controls
| Control | Breaches |
|---|---|
| C08 Untrusted-input isolation | 111 (96% of applicable cases) |
| C02 Approval gate | 72 |
| C04 Policy limits | 65 |
| C01 Least privilege | 64 |
| C14 No auto-execution of config | 45 |
| C10 Secret protection | 45 |

## What predicts severity
- **Breadth.** Each additional governance domain implicated raises the odds of a High or Critical rating by a factor of 2.28 (p < .001). The rate is 41% for single-domain cases and 78% or more for cases with two or more domains.
- **The GCS alone does not predict severity.** OR = 1.34 per SD, p = .057, and the estimate is unstable across coders.
- **Top predictive features** in the best model: D1 present, number of domains, C01 breached, C14 breached, C08 breached, C11 breached.
- **Best model:** a random forest on ACEG + CWE-group features.
  - Cross-validated AUC .85; hold-out AUC .84.
  - With fully automated LLM coding, hold-out AUC .81.
  - For comparison, CWE-only triage reaches AUC .70.

## Reliability of LLM coding (LLM against human consensus)
| Measure | κ |
|---|---|
| Pooled across domains | .58 (human–human .28) |
| D5 | .74 |
| D6 | .63 |
| D4 | .60 |
| D8 | .32 |
| D1 | .28 |
| D2 | .25 |
| Primary domain | .30 |

The LLM tends to over-code D2 and D7. Keep a human reviewer on D1, D2, D3, D7, D8 and the primary domain.

## Caveats
- Disclosure bias: vendors with active security programmes publish more, so counts are not safety rankings.
- CVSS measures technical severity, not business impact.
- 99% of cases date from 2025 to 2026, so recalibrate as agents change.
