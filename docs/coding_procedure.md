# Coding Procedure — Weeks 2 to 5

How the group produces the human gold labels for all 223 cases. The tools are:

- `coding/ACEG_coding_workbook.xlsx`, the coding workbook;
- `docs/codebook.md`, the coding rules;
- `src/05_pilot_kappa.py` and `src/06_build_coded_dataset.py`, the checking and build scripts.

## Roles

| Role | Responsibility |
|---|---|
| Coder 1 | Codes every case on the **Coder1** sheet. |
| Coder 2 | Codes every case on the **Coder2** sheet. |
| Adjudicator | Resolves any disagreement the two coders cannot settle. This can be a third group member or the mentor. |

Enter the names on the **Tracker** sheet.

## Ground rules

1. **Code independently.** Do not open the other coder's sheet until the batch is finished, and do not discuss individual cases while coding.
2. **Use only the advisory text and its link** on the **Cases** sheet. Do not use outside knowledge of the product.
3. **Do not use any AI tool to code.** The human labels are the reference standard that the Claude pipeline is tested against in RQ4. AI-assisted human codes would make that test circular.
4. **Fix every message in the `check` column** before moving on. A row counts as done only when `done` = 1.
5. **Work on a shared copy.** Keep the workbook in a shared folder (OneDrive or Google Drive, opened in Excel) and keep a dated backup each week.

## Week 2 — pilot (20 cases)

1. Both coders read `docs/codebook.md`, including the worked example (CA-018), and the README sheet.
2. Both coders code the 20 rows marked **W2 pilot**. Allow about 10 minutes per case.
3. Check agreement:
   - the **Agreement** sheet updates live as you work;
   - for the formal result, run `python src/05_pilot_kappa.py`.
4. Any item with κ < .60 is a **wording problem, not a coder problem**. Discuss the disagreements and reword that domain or control in `docs/codebook.md`. Record the change in `docs/framework_changelog.md` as v1.1.
5. **Adjudicate the 20 pilot rows.** Where the coders disagree, a Gold cell stays blank and turns pink; type the agreed value into it.

## Weeks 3–5 — main coding (203 cases)

| Batch | Cases | Coding | Adjudication |
|---|---|---|---|
| W3 | 68 | Week 3 | End of Week 3 |
| W4 | 68 | Week 4 | End of Week 4 |
| W5 | 67 | Week 5 | End of Week 5 |

Each coder needs about 11–12 hours per week.

- **Once a week:**
  - run `python src/05_pilot_kappa.py --all` to watch agreement;
  - adjudicate that week's pink Gold cells;
  - check progress on the **Tracker** sheet.
- **If agreement drops below κ = .60 on any domain,** stop and discuss before continuing. Do not change the codebook after Week 2 unless the group agrees; any change is logged.

## End of Week 5 — build the dataset

```bash
python src/06_build_coded_dataset.py
```

The script runs these steps:

1. It takes the agreed value when both coders match, and the adjudicated value when they do not.
2. It checks that every row is complete and consistent.
3. It computes GCS, the number of domains, and the domain family.
4. It writes `data/processed/cases_coded.csv`, together with:
   - `outputs/interrater_kappa_full.csv`, reported in the final report as the reliability of the human coding;
   - `outputs/adjudication_log.csv`, which records every resolved disagreement.

If anything is unresolved or inconsistent, the script stops and lists the affected cases.

## Weeks 5–6 — LLM pipeline

```bash
export ANTHROPIC_API_KEY=...        # never commit this key
python src/03_llm_code.py           # writes data/processed/llm_codes.csv
python src/06_build_coded_dataset.py   # re-run to merge the LLM codes
python src/04_analysis.py           # RQ1–RQ4 results in outputs/
```
