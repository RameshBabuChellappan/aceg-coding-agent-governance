"""Step 8 - clean the two human coders' workbooks, build 2-of-3 majority labels, and
load everything into the project SQLite database (data/aceg.db).

Cleaning (logged in outputs/final/tables/cleaning_log_coding.csv)
  R1  controls coded for a domain the same coder marked absent are set to NA (codebook rule 4);
  R2  values are normalised to 1 / 0 / NA.
Final ("gold") labels: majority of Coder 1, Coder 2 and the LLM coder, cell by cell.
  domains     d = 1 when at least 2 of 3 code it present; if no domain reaches 2 votes,
              the domain(s) with the most votes, ties broken by CAUSAL_ORDER;
  primary     the majority primary domain if it is present in the final labels; otherwise the
              present domain with most primary votes, then most domain votes, then CAUSAL_ORDER;
  controls    for each control of a present domain, majority of the non-NA votes; a 1-1 tie is
              coded 0 (codebook: 0 = not shown to be breached); a present domain left with no
              breached control receives one breach on its control with the most 1-votes;
  covered     majority of the three votes.
RQ4 does not use these labels: it scores the LLM only where the two humans agree.
"""
import sqlite3
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from aceg_common import ROOT, DOM, CTRL, LINK, CAUSAL_ORDER, derive

FIELDS = DOM + ["primary_domain"] + CTRL + ["covered"]


def read_sheet(path, sheet):
    wb = load_workbook(path)
    cases = [r[0] for r in wb["Cases"].iter_rows(min_row=2, max_col=1, values_only=True)]
    ws = wb[sheet]
    hdr = [c.value for c in ws[1]]
    rows = []
    for r in ws.iter_rows(min_row=2, max_row=len(cases) + 1, values_only=True):
        rec = dict(zip(hdr, r))
        out = {}
        for f in FIELDS:
            v = rec[f]
            out[f] = np.nan if v is None or str(v).strip().upper() in ("", "NA") else float(v)
        rows.append(out)
    df = pd.DataFrame(rows)
    df.insert(0, "case_id", cases)
    return df


def clean(df, coder):
    log = []
    df = df.copy()
    for i, r in df.iterrows():
        for d, cs in LINK.items():
            if r[f"d{d}"] != 1:
                for c in cs:
                    col = f"c{c:02d}"
                    if pd.notna(r[col]):
                        log.append({"coder": coder, "case_id": r.case_id, "field": col,
                                    "rule": "R1 control coded for absent domain", "old": r[col], "new": "NA"})
                        df.at[i, col] = np.nan
    return df, log


def majority(c1, c2, c3):
    g = []
    for i in range(len(c1)):
        rows = [c1.iloc[i], c2.iloc[i], c3.iloc[i]]
        rec = {"case_id": c1.case_id.iloc[i]}
        votes = {d: sum(int(r[f"d{d}"] == 1) for r in rows) for d in range(1, 9)}
        present = [d for d in range(1, 9) if votes[d] >= 2]
        rule_dom = "majority"
        if not present:
            top = max(votes.values())
            present = [d for d in CAUSAL_ORDER if votes[d] == top][:1]
            rule_dom = "fallback-most-votes"
        for d in range(1, 9):
            rec[f"d{d}"] = int(d in present)
        prim_votes = [int(r.primary_domain) for r in rows if pd.notna(r.primary_domain)]
        cnt = {p: prim_votes.count(p) for p in set(prim_votes)}
        best = [p for p, k in cnt.items() if k >= 2 and p in present]
        if best:
            rec["primary_domain"], rule_p = best[0], "majority"
        else:
            cand = sorted(present, key=lambda d: (-cnt.get(d, 0), -votes[d], CAUSAL_ORDER.index(d)))
            rec["primary_domain"], rule_p = cand[0], "tie-break"
        for d, cs in LINK.items():
            for c in cs:
                col = f"c{c:02d}"
                if d not in present:
                    rec[col] = np.nan
                    continue
                v = [r[col] for r in rows if pd.notna(r[col])]
                ones, zeros = sum(x == 1 for x in v), sum(x == 0 for x in v)
                rec[col] = 1 if ones > zeros else 0
            if d in present and not any(rec[f"c{c:02d}"] == 1 for c in cs):
                ones = {c: sum(int(r[f"c{c:02d}"] == 1) for r in rows) for c in cs}
                pick = max(cs, key=lambda c: (ones[c], -cs.index(c)))
                rec[f"c{pick:02d}"] = 1
        rec["covered"] = int(sum(int(r.covered == 1) for r in rows) >= 2)
        rec["rule_domains"], rec["rule_primary"] = rule_dom, rule_p
        rec["unanimous_domains"] = int(all(votes[d] in (0, 3) for d in range(1, 9)))
        g.append(rec)
    return pd.DataFrame(g)


def main():
    cw = ROOT / "coding/completed"
    c1, log1 = clean(read_sheet(cw / "ACEG_coding_workbook_coder1_completed.xlsx", "Coder1"), "Coder 1")
    c2, log2 = clean(read_sheet(cw / "ACEG_coding_workbook_coder2_completed.xlsx", "Coder2"), "Coder 2")
    llm = pd.read_csv(ROOT / "data/processed/llm_codes.csv")[["case_id"] + FIELDS]
    assert (c1.case_id.values == c2.case_id.values).all()
    llm = llm.set_index("case_id").loc[c1.case_id].reset_index()
    gold = majority(c1, c2, llm)
    src = pd.read_csv(ROOT / "data/processed/cases_to_code.csv")
    pd.DataFrame(log1 + log2).to_csv(ROOT / "outputs/final/tables/cleaning_log_coding.csv", index=False)

    out = {}
    for name, df in {"coder1": c1, "coder2": c2, "llm": llm, "gold": gold}.items():
        d = derive(df)
        d.to_csv(ROOT / f"data/processed/codes_{name}.csv", index=False)
        out[name] = d
    coded = src.merge(out["gold"], on="case_id")
    coded.to_csv(ROOT / "data/processed/cases_coded.csv", index=False)

    db = ROOT / "data/aceg.db"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    src.to_sql("cases", con, index=False)
    for name, d in out.items():
        d.assign(source=name).to_sql(f"codes_{name}", con, index=False)
    pd.DataFrame(log1 + log2).to_sql("cleaning_log", con, index=False)
    con.executescript("""
    CREATE UNIQUE INDEX ix_cases ON cases(case_id);
    CREATE UNIQUE INDEX ix_gold ON codes_gold(case_id);
    CREATE VIEW v_analysis AS
      SELECT c.case_id, c.product, c.component_type, c.year, c.published, c.cvss_severity,
             c.cvss_score, c.high_impact, c.user_interaction_required, c.cwe_ids,
             g.*
      FROM cases c JOIN codes_gold g USING (case_id);
    CREATE VIEW v_agreement AS
      SELECT a.case_id, a.d1 AS c1_d1, b.d1 AS c2_d1, l.d1 AS llm_d1, a.primary_domain AS c1_p,
             b.primary_domain AS c2_p, l.primary_domain AS llm_p
      FROM codes_coder1 a JOIN codes_coder2 b USING (case_id) JOIN codes_llm l USING (case_id);
    """)
    con.commit()
    tabs = con.execute("select name, type from sqlite_master where type in ('table','view')").fetchall()
    print(tabs)
    print("R1 corrections:", len(log1), len(log2))
    print(gold.rule_domains.value_counts().to_dict(), gold.rule_primary.value_counts().to_dict(),
          "unanimous", gold.unanimous_domains.sum())
    con.close()


if __name__ == "__main__":
    main()
