# ACEG coding skill (Version 1, used for the final report)

Purpose: turn the text of one public coding-agent security advisory into ACEG codes that the
scorecard service (`src/10_scorecard_service.py`, `POST /score`) accepts.

## Inputs
- Title, product, component type, publication date, description of the advisory.
- Remove or mask any severity wording (CVSS score, "critical", "high severity") before coding.

## Instructions given to the LLM
You are a careful research coder applying the Agentic Coding Ethics and Governance (ACEG) codebook.
Use only the advisory text. Do not use outside knowledge and do not guess severity.
1. For each domain D1–D8, code 1 if the text shows the domain's requirement was breached or could be
   breached, otherwise 0 (definitions in docs/codebook.md, section 2).
2. Choose one primary domain: the domain that most directly enabled the weakness; ties go to the
   earliest point in the causal chain.
3. For each control linked to a domain coded 1, list it as breached only if the text shows it was
   absent, failed, or was bypassed. Unlisted applicable controls are coded 0. Controls of absent
   domains are not applicable.
4. covered = 1 if at least one breached control would plausibly have prevented the weakness.
5. Quote the sentence that supports each domain coded 1 (evidence field).

## Output (one line or one JSON object per case)
`case_id | domains present | primary domain | breached controls | covered`
e.g. `CA-018|1,4|1|02,08|1`, or JSON:
`{"case_id": "...", "domains": [1,4], "primary_domain": 1, "breached_controls": [2,8], "covered": 1,
  "cwe_ids": "CWE-78", "component_type": "agent product", "year": 2026, "evidence": {...}}`

## Review rule (from RQ4)
Accept LLM codes for D4, D5 and D6 after spot checks; route D1, D2, D3, D7 and D8 and the primary
domain to a human reviewer.
