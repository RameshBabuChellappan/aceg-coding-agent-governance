# ACEG framework change log

| Version | Date | Change | Evidence (RQ, statistic, case IDs) |
|---|---|---|---|
| v1 | 2026-10-11 | Eight governance domains (D1–D8), four families and twenty controls (C01–C20). Derived from the literature, OWASP Top 10 for Agentic Applications (2026), NIST AI RMF and ISO/IEC 42001. | docs/codebook.md |
| v1.1 | not issued | Pilot double coding ran with the main batches, so wording was not revised mid-coding | Final report, RQ4 |
| v2 (proposed) | 2026-11-10 | Merge D3 and D7 into one Transparency and accountability domain with explicit triggers | Human κ = .00 for D3 and D7; Coder 1 coded D3 in 57.8% of cases, Coder 2 in 0% |
| v2 (proposed) | 2026-11-10 | Decision rule: bypass of a configured limit = D2 (primary); action without approval = D1 | κ = .16 (D1), .22 (D2); LLM over-coded D2 in 44 consensus-negative cases |
| v2 (proposed) | 2026-11-10 | `covered` must name the preventing control (evidence field) | Coder 1 coded covered = 1 for all 223 cases |
| v2 (proposed) | 2026-11-10 | New C21 Authenticated, origin-checked local agent endpoints | 15 cases (e.g., CA-070, CA-117, CA-214) |
| v2 (proposed) | 2026-11-10 | New C22 Transport and host verification for remote sessions | Only uncovered case CA-121 |
| v2 (proposed) | 2026-11-10 | Review C07, C16, C20 (never breached) for merging; keep C01, C08, C11, C14 as scorecard priorities | Table B1; permutation importance (Figure 6) |
