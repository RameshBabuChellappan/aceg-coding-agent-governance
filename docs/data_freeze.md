# Data freeze

The analysis dataset was frozen on **11 October 2026**. Both sources were cloned at the commits below. Re-running `src/01_collect.py` and `src/02_screen.py` on these commits reproduces `data/interim/candidates.csv` (239 records) and `data/processed/cases_to_code.csv` (223 cases) exactly.

| Source | Repository | Commit | Commit date | Licence / terms |
|---|---|---|---|---|
| GitHub Advisory Database | https://github.com/github/advisory-database | fb63b5aae38c79bfe8c7a8099df71f8ab1349da8 | 2026-10-11 | CC BY 4.0 |
| CVE List V5 | https://github.com/CVEProject/cvelistV5 | a526d812d239059b4f9e6e9eb8fbead8b2e21a82 | 2026-10-11 | CVE Program Terms of Use |

To check out the exact versions: `git -C data/raw/advisory-database fetch --depth 1 origin <commit> && git -C data/raw/advisory-database checkout <commit>` (same for `cvelistV5`).
