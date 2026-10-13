# Governing Agentic AI Coding Assistants in the Software Industry

**Building and evaluating the Agentic Coding Ethics and Governance (ACEG) Framework on public vulnerability data.**

QM640 Data Analytics Capstone · Walsh College · Group 3 · Ramesh Babu Chellappan · Mentor: Mr. Jainesh Garg

This repository holds the data, code and documentation for the capstone. The study builds the ACEG framework for AI coding and software-engineering agents: eight governance domains, grouped into four families, with twenty controls. It then applies the framework to **all 223 eligible public security advisories and CVE records** published from 2023 to 11 October 2026 for agents such as Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Roo Code, Kiro and Gemini CLI, together with the tools that extend them.

Each case receives a **Governance Compliance Score (GCS)**: the share of relevant framework controls that held. The study then tests four research questions:

| RQ | Question | Main method |
|---|---|---|
| RQ1 | What share of cases does the ACEG framework cover, and how prevalent is each governance domain? | Proportions with Wilson 95% CI; exact binomial test (H0: coverage ≤ 80%) |
| RQ2 | Is the governance domain family associated with whether exploitation requires human interaction? | Chi-square test of independence; Cramér's V |
| RQ3 | Does a lower GCS predict a high-impact case (CVSS High or Critical)? | Binary logistic regression (odds ratios, AUC, Hosmer–Lemeshow, Box–Tidwell); sensitivity checks (product-clustered SEs, CVSS version, CVSS-score regression); random forest benchmark with permutation importance |
| RQ4 | How accurately does an automated LLM pipeline apply the framework compared with human gold labels? | Cohen's κ, accuracy, precision, recall, F1 |

## Data (public, frozen 11 October 2026)

| File | Content |
|---|---|
| `data/interim/candidates.csv` | 239 records identified in the GitHub Advisory Database and CVE List V5 |
| `docs/screening_decisions.csv` | 16 exclusions, each with its reason |
| `data/processed/cases_to_code.csv` | **223 eligible cases**: 176 agent products and 47 ecosystem components; 70% High or Critical |
| `data/processed/cases_coded_TEMPLATE.csv` | Column layout of the coded dataset, with one worked example (CA-018) |

`docs/data_freeze.md` records the exact source commits. `data/raw/README.md` shows how to download the raw sources with `git`; no account or API key is needed.

## Repository structure

```
README.md                    this file
LICENSE                      MIT (code); CC BY 4.0 (annotations and codebook)
requirements.txt             Python packages
data/raw/README.md           how to download both sources (raw clones are not committed)
data/interim/                candidates.csv
data/processed/              cases_to_code.csv; cases_coded_TEMPLATE.csv; cases_coded.csv (after coding)
docs/codebook.md             ACEG framework: domains D1–D8, controls C01–C20, scoring rules, worked example
docs/data_dictionary.csv     every variable with type, meaning, units and role
docs/screening_decisions.csv exclusions with reasons
docs/data_freeze.md          source commits and dates
docs/framework_changelog.md  v1 → v2 changes with evidence
docs/coding_procedure.md     Week 2–5 procedure: pilot, double coding, adjudication
coding/ACEG_coding_workbook.xlsx  coding workbook (Coder1, Coder2, Gold, Agreement, Tracker)
coding/pilot_cases.csv       the 20 stratified pilot cases
tools/build_workbook.py      rebuilds the coding workbook from cases_to_code.csv
sample_size/sample_size.py   reproduces the RQ1–RQ4 sample-size calculations
src/01_collect.py            identify coding-agent records in both sources
src/02_screen.py             apply eligibility rules; PRISMA-style counts; number cases
src/03_llm_code.py           LLM pipeline that applies the codebook to each case
src/04_analysis.py           RQ1–RQ4 statistics, models and evaluation metrics
src/05_pilot_kappa.py        inter-coder κ for the pilot (or --all for every finished row)
src/06_build_coded_dataset.py  gold labels + checks -> data/processed/cases_coded.csv (merges LLM codes)
src/coding_io.py             shared helpers for reading the workbook
tests/make_synthetic.py      random codes on the real cases to check the pipeline runs (not results)
outputs/                     tables and summaries written by the scripts
```

## How to reproduce

```bash
pip install -r requirements.txt
python sample_size/sample_size.py          # N = max(196, 175, 187, 171) = 196; all 223 eligible cases are used
# 1. download the sources (data/raw/README.md), then:
python src/01_collect.py                   # -> data/interim/candidates.csv (239)
python src/02_screen.py                    # -> data/processed/cases_to_code.csv (223), outputs/screening_flow.csv
# 2. Weeks 2–5: two coders code every case in coding/ACEG_coding_workbook.xlsx (docs/coding_procedure.md)
python src/05_pilot_kappa.py               # Week 2 pilot reliability; --all for weekly checks
python src/06_build_coded_dataset.py       # end of Week 5 -> data/processed/cases_coded.csv
export ANTHROPIC_API_KEY=...               # 3. automated pipeline
python src/03_llm_code.py                  # -> data/processed/llm_codes.csv
python src/06_build_coded_dataset.py       # re-run to merge the LLM codes
python src/04_analysis.py                  # 4. results -> outputs/
```

Check the analysis code before coding is finished:

```bash
python tests/make_synthetic.py && python src/04_analysis.py tests/synthetic_cases.csv
```

## Ethics

- Only public, already-disclosed records are used. No human participants are involved and no organizational data is collected.
- No exploit code is reproduced.
- Reporter names are not copied into the coded data.
- Sources are attributed under their terms (CC BY 4.0; CVE Program Terms of Use).

## Licence

- Code: MIT.
- Annotations, codebook and data dictionary: CC BY 4.0.
- Source records remain under their original terms.
