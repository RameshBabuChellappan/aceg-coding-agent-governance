"""Build Group3_QM640_Statistical_Calculations.xlsx — every statistic in the final report,
recomputed with live Excel formulas and explained step by step in plain language."""
import json, sys
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.comments import Comment

ROOT = "/home/claude/work/repo"
sys.path.insert(0, ROOT + "/src")
from cvss31 import base_score

OUT = "/home/claude/xlsx/Group3_QM640_Statistical_Calculations.xlsx"
S = json.load(open(f"{ROOT}/outputs/final/summary.json"))
T = lambda n: pd.read_csv(f"{ROOT}/outputs/final/tables/{n}.csv")

# ---------------------------------------------------------------- data prep
c = pd.read_csv(f"{ROOT}/data/processed/cases_coded.csv").sort_values("case_id").reset_index(drop=True)
v3 = c.cvss_vector.map(base_score)
rec = c.cvss_score.isna() & v3.notna()
c["cvss_final"] = c.cvss_score.where(~rec, v3)
c["cvss_rec"] = rec.astype(int)
CWE_GROUPS = [("Command injection", {"77", "78", "88"}),
              ("Code injection", {"94", "95", "1336", "79"}),
              ("Path traversal / link following", {"22", "23", "59", "61", "641", "73"}),
              ("Access control / authentication", {"284", "285", "287", "288", "306", "862", "863", "269",
                                                    "276", "732", "1188", "639", "346", "942", "352", "940"}),
              ("Information exposure", {"200", "201", "212", "312", "319", "522", "532", "538", "552",
                                        "668", "310", "322", "297"}),
              ("Untrusted input / prompt injection", {"20", "74", "116", "150", "1427", "1426", "184", "178",
                                                     "183", "436", "693", "807"}),
              ("Untrusted configuration / inclusion", {"15", "829", "426", "427", "494", "506", "1385",
                                                       "749", "501", "356", "350", "696", "515", "377",
                                                       "367", "918", "601"})]


def cwe_group(s):
    ids = [x.strip().replace("CWE-", "") for x in str(s).split(";") if x.strip()]
    for name, g in CWE_GROUPS:
        if any(i in g for i in ids):
            return name
    return "Other"


c["cwe_group"] = c.cwe_ids.map(cwe_group)
codes = {k: pd.read_csv(f"{ROOT}/data/processed/codes_{k}.csv").set_index("case_id").loc[c.case_id].reset_index()
         for k in ("coder1", "coder2", "llm", "gold")}
tp = pd.read_csv(f"{ROOT}/outputs/final/test_predictions.csv")
N = len(c)
R1, RN = 2, N + 1
LINK = {1: [1, 2, 3], 2: [4, 5], 3: [6, 7], 4: [8, 9], 5: [10, 11], 6: [12, 13, 14], 7: [15, 16, 17], 8: [18, 19, 20]}
DNAME = {1: "D1 Agency and action control", 2: "D2 Instruction and boundary adherence",
         3: "D3 Transparency and honest reporting", 4: "D4 Input trust and goal integrity",
         5: "D5 Secrets and data protection", 6: "D6 Code and supply-chain integrity",
         7: "D7 Accountability and recoverability", 8: "D8 Human oversight and reliance"}
FAM = {1: "A", 2: "A", 3: "D", 4: "B", 5: "C", 6: "B", 7: "D", 8: "A"}

# ---------------------------------------------------------------- styles
AR = "Arial"
F_IN = Font(name=AR, size=10, color="0000FF")
F_CALC = Font(name=AR, size=10, color="000000")
F_LINK = Font(name=AR, size=10, color="008000")
F_TXT = Font(name=AR, size=10, color="000000")
F_H = Font(name=AR, size=10, bold=True, color="FFFFFF")
F_T = Font(name=AR, size=14, bold=True, color="1F3864")
F_ST = Font(name=AR, size=10, italic=True, color="404040")
F_SEC = Font(name=AR, size=11, bold=True, color="1F3864")
F_OK = Font(name=AR, size=10, bold=True, color="006100")
FILL_H = PatternFill("solid", fgColor="1F3864")
FILL_SEC = PatternFill("solid", fgColor="D9E1F2")
FILL_KEY = PatternFill("solid", fgColor="FFF2CC")
FILL_EXPL = PatternFill("solid", fgColor="F7F9FC")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="top", wrap_text=True)

wb = Workbook()
wb.remove(wb.active)
REG = {}  # global name -> (sheet, address)


def q(sheet):
    return f"'{sheet}'"


def ref(name, here):
    sh, a = REG[name]
    return a if sh == here else f"{q(sh)}!{a}"


def fill(tmpl, here):
    import re
    return re.sub(r"\{([A-Za-z0-9_.]+)\}", lambda m: ref(m.group(1), here), tmpl)


class Calc:
    """A calculation tab laid out as: Step | What we calculate | Value | Maths | Excel formula | Plain-language | Report | Check"""
    HEAD = ["Step", "What we calculate", "Value", "The maths", "Excel formula used in the Value cell",
            "Plain-language explanation (for learner and mentor)", "Value in the report", "Check"]
    WID = [6, 34, 15, 34, 44, 70, 13, 13]

    def __init__(self, name, title, subtitle, section_ref):
        self.name = name
        self.ws = wb.create_sheet(name)
        ws = self.ws
        for i, w in enumerate(self.WID, 1):
            ws.column_dimensions[L(i)].width = w
        ws["A1"] = title; ws["A1"].font = F_T
        ws["A2"] = subtitle; ws["A2"].font = F_ST; ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells("A2:H2"); ws.row_dimensions[2].height = 44
        ws["A3"] = "Report section: " + section_ref; ws["A3"].font = F_ST
        ws["A3"].hyperlink = None
        self.r = 5
        self.step = 0
        self.header()
        ws.freeze_panes = "A6"

    def header(self):
        for i, h in enumerate(self.HEAD, 1):
            cl = self.ws.cell(self.r, i, h); cl.font = F_H; cl.fill = FILL_H; cl.alignment = CENTER; cl.border = BOX
        self.r += 1

    def section(self, text):
        ws = self.ws
        self.r += 0
        cl = ws.cell(self.r, 1, text); cl.font = F_SEC
        for i in range(1, 9):
            ws.cell(self.r, i).fill = FILL_SEC
        self.r += 1

    def row(self, key, what, formula, maths, explain, report=None, tol=None, fmt="0.000", kind="calc", key_row=False):
        """kind: calc (black formula), input (blue hardcoded), link (green cross-sheet)."""
        ws, r = self.ws, self.r
        self.step += 1
        ws.cell(r, 1, self.step).alignment = CENTER
        ws.cell(r, 2, what).alignment = WRAP
        v = fill(formula, self.name) if isinstance(formula, str) and formula.startswith("=") else formula
        cv = ws.cell(r, 3, v)
        cv.number_format = fmt
        cv.alignment = Alignment(vertical="top", horizontal="right")
        cv.font = {"calc": F_CALC, "input": F_IN, "link": F_LINK}[kind]
        if kind == "input" and not (isinstance(v, str) and v.startswith("=")):
            pass
        ws.cell(r, 4, maths).alignment = WRAP
        ws.cell(r, 5, (" " + v) if isinstance(v, str) and v.startswith("=") else "(typed input – see explanation)").alignment = WRAP
        ws.cell(r, 5).font = Font(name="Courier New", size=9, color="595959")
        ws.cell(r, 6, explain).alignment = WRAP
        ws.cell(r, 6).fill = FILL_EXPL
        if report is not None:
            rc = ws.cell(r, 7, report); rc.font = F_IN; rc.number_format = fmt
            t = tol if tol is not None else 0.0015
            ck = ws.cell(r, 8, f'=IF(ABS(C{r}-G{r})<={t},"✓ matches","check")'); ck.font = F_OK
        for i in range(1, 9):
            ws.cell(r, i).border = BOX
            if ws.cell(r, i).font is None or i not in (3, 5, 7, 8):
                if i not in (3, 5, 7, 8):
                    ws.cell(r, i).font = F_TXT
        if key_row:
            cv.fill = FILL_KEY
        ws.row_dimensions[r].height = max(30, 13.5 * (1 + max(len(explain) // 68, len(str(maths)) // 30, len(what) // 32)))
        if key:
            REG[key] = (self.name, f"$C${r}")
        self.r += 1
        return f"$C${r}"

    def note(self, text, h=None):
        ws = self.ws
        cl = ws.cell(self.r, 2, text); cl.alignment = WRAP; cl.font = F_ST
        ws.merge_cells(start_row=self.r, start_column=2, end_row=self.r, end_column=8)
        ws.row_dimensions[self.r].height = h or max(18, 14 * (1 + len(text) // 170))
        self.r += 1

    def blank(self, n=1):
        self.r += n

    def table(self, headers, rows, start_col=2, widths=None, fmts=None, kinds=None, key_prefix=None, explain=None):
        """rows: list of lists; strings beginning with '=' are formulas ({rr} = this row, {name} registry)."""
        ws = self.ws
        r0 = self.r
        for j, h in enumerate(headers):
            cl = ws.cell(self.r, start_col + j, h); cl.font = F_H; cl.fill = FILL_H; cl.alignment = CENTER; cl.border = BOX
        ws.row_dimensions[self.r].height = 30
        self.r += 1
        first = self.r
        for row in rows:
            for j, val in enumerate(row):
                if isinstance(val, str) and val.startswith("="):
                    val = fill(val.replace("{rr}", str(self.r)), self.name)
                cl = ws.cell(self.r, start_col + j, val)
                cl.border = BOX
                k = (kinds[j] if kinds else "calc")
                if isinstance(val, str) and not val.startswith("=") and k != "input":
                    cl.font = F_TXT
                else:
                    cl.font = {"calc": F_CALC, "input": F_IN, "link": F_LINK, "text": F_TXT}[k]
                if fmts and fmts[j]:
                    cl.number_format = fmts[j]
                cl.alignment = Alignment(vertical="top", wrap_text=True)
            self.r += 1
        last = self.r - 1
        if explain:
            cl = ws.cell(r0, start_col + len(headers) + 0 if start_col + len(headers) <= 8 else 9, None)
        self.r += 1
        return first, last


def col_of(table_first_col, j):
    return L(table_first_col + j)


# =============================================================== 9 RQ3 logistic (coefficient block first: Data needs it)
lg = T("rq3_logit_model2")
rq3 = Calc("09_RQ3_Logistic", "RQ3 – Logistic regression: does a higher GCS predict a high-impact vulnerability?",
           "Model 2: logit P(high impact) = b0 + b1·GCS(z) + b2·Ecosystem + b3·NumberOfDomains + b4·Published2026. "
           "Excel cannot run the iterative maximum-likelihood search, so the five coefficients (from Python, Newton–Raphson) are typed in blue. "
           "Everything after that – predictions, log-likelihood, LR test, McFadden R², standard errors (via the inverse information matrix), z, p, odds ratios, CIs and VIFs – is recomputed live.",
           "Section 4 Results – RQ3 (Table: Model 2 logistic regression) and assumption checks")
rq3.section("A. Coefficients from the maximum-likelihood fit (inputs)")
BN = ["b0", "b1", "b2", "b3", "b4"]
TERMS = ["Intercept", "GCS (per SD)", "Ecosystem component", "Number of domains", "Published in 2026"]
for i, (bn, tm) in enumerate(zip(BN, TERMS)):
    rq3.row(f"rq3.{bn}", f"Coefficient {bn} – {tm}", float(lg.b[i]), f"{bn} (log-odds units)",
            ["The baseline log-odds of high impact when every predictor is 0 (GCS at its average, a non-ecosystem component, 0 domains, published before 2026).",
             "How much the log-odds of high impact change when GCS rises by one standard deviation (about 13.7 points), holding the other predictors fixed.",
             "Change in log-odds for an ecosystem component (plugin, extension, MCP server) versus a core product.",
             "Change in log-odds for each additional ACEG domain the incident touches.",
             "Change in log-odds for incidents published in 2026 versus earlier years."][i]
            + " Typed in from Python (src/09_final_analysis.py, logit_fit) – Excel has no built-in logistic regression; the score check in Part C proves these are the best-fitting values.",
            fmt="0.0000", kind="input")

# =============================================================== DATA sheet
dcols = ["case_id", "product", "component_type", "year", "cvss_score", "cvss_recovered", "severity", "high_impact",
         "ui_required", "cwe_group"] + [f"d{j}" for j in range(1, 9)] + ["primary_domain", "family"] + \
        [f"c{i:02d}" for i in range(1, 21)] + ["covered", "n_domains", "n_applicable", "n_breached", "gcs",
        "ecosystem", "year_2026", "gcs_z", "x_eco", "x_ndom", "x_y26", "x_gz2", "x_eco2", "x_ndom2",
        "eta", "p_hat", "ll_term", "w", "p_rank", "p_rank_py", "hl_group", "hl_group_row", "gcs_rank", "gcs_ties"]
DC = {n: L(i + 1) for i, n in enumerate(dcols)}


def DR(n, sheet="Data"):
    return f"{sheet}!${DC[n]}${R1}:${DC[n]}${RN}"


ws = wb.create_sheet("Data")
FORM = {"family", "n_domains", "n_applicable", "n_breached", "gcs", "ecosystem", "year_2026", "gcs_z", "x_eco",
        "x_ndom", "x_y26", "x_gz2", "x_eco2", "x_ndom2", "eta", "p_hat", "ll_term", "w", "p_rank", "hl_group",
        "hl_group_row", "gcs_rank", "gcs_ties"}
for j, n in enumerate(dcols, 1):
    cl = ws.cell(1, j, n); cl.font = F_H; cl.fill = FILL_H if n not in FORM else PatternFill("solid", fgColor="375623")
    cl.alignment = CENTER
    ws.column_dimensions[L(j)].width = 12 if n not in ("product", "cwe_group") else 26
ws.column_dimensions["A"].width = 10
ws.freeze_panes = "B2"
b = {k: ref(f"rq3.{k}", "Data") for k in BN}
_X = np.column_stack([np.ones(N), ((c.gcs - c.gcs.mean()) / c.gcs.std(ddof=0)).values, (c.component_type == "ecosystem").astype(int),
                      c.n_domains.values, (c.year == 2026).astype(int)])
_p = 1 / (1 + np.exp(-_X @ lg.b.values))
PYRANK = np.empty(N, int); PYRANK[np.argsort(_p)] = np.arange(1, N + 1)
for i, rw in c.iterrows():
    r = i + 2
    vals = {"case_id": rw.case_id, "product": rw["product"], "component_type": rw.component_type, "year": int(rw.year),
            "cvss_score": None if pd.isna(rw.cvss_final) else float(rw.cvss_final), "cvss_recovered": int(rw.cvss_rec),
            "severity": rw.cvss_severity, "high_impact": int(rw.high_impact),
            "ui_required": None if pd.isna(rw.user_interaction_required) else int(rw.user_interaction_required),
            "cwe_group": rw.cwe_group, "p_rank_py": int(PYRANK[i]), "primary_domain": int(rw.primary_domain), "covered": int(rw.covered)}
    for j in range(1, 9):
        vals[f"d{j}"] = int(rw[f"d{j}"])
    for k in range(1, 21):
        v = rw[f"c{k:02d}"]
        vals[f"c{k:02d}"] = None if pd.isna(v) else int(v)
    D = lambda n: f"{DC[n]}{r}"
    cr = f"{DC['c01']}{r}:{DC['c20']}{r}"
    f = {"family": f'=CHOOSE({D("primary_domain")},"A","A","D","B","C","B","D","A")',
         "n_domains": f"=SUM({DC['d1']}{r}:{DC['d8']}{r})",
         "n_applicable": "=" + "+".join(f"{len(LINK[j])}*{D(f'd{j}')}" for j in range(1, 9)),
         "n_breached": f"=COUNTIF({cr},1)",
         "gcs": f"=IF({D('n_applicable')}=0,\"\",100*({D('n_applicable')}-{D('n_breached')})/{D('n_applicable')})",
         "ecosystem": f'=IF({D("component_type")}="ecosystem",1,0)',
         "year_2026": f"=IF({D('year')}=2026,1,0)",
         "gcs_z": f"=({D('gcs')}-AVERAGE({DR('gcs','x')[2:].replace('x!','')}))/STDEVP({DR('gcs','x')[2:].replace('x!','')})",
         "x_eco": f"={D('ecosystem')}", "x_ndom": f"={D('n_domains')}", "x_y26": f"={D('year_2026')}",
         "x_gz2": f"={D('gcs_z')}", "x_eco2": f"={D('ecosystem')}", "x_ndom2": f"={D('n_domains')}",
         "eta": f"={b['b0']}+{b['b1']}*{D('gcs_z')}+{b['b2']}*{D('x_eco')}+{b['b3']}*{D('x_ndom')}+{b['b4']}*{D('x_y26')}",
         "p_hat": f"=1/(1+EXP(-{D('eta')}))",
         "ll_term": f"={D('high_impact')}*LN({D('p_hat')})+(1-{D('high_impact')})*LN(1-{D('p_hat')})",
         "w": f"={D('p_hat')}*(1-{D('p_hat')})",
         "p_rank": f"=SUMPRODUCT(--(${DC['p_hat']}${R1}:${DC['p_hat']}${RN}<{D('p_hat')}))+COUNTIF(${DC['p_hat']}${R1}:{D('p_hat')},{D('p_hat')})",
         "hl_group": f"=IF({D('p_rank_py')}<=69,INT(({D('p_rank_py')}-1)/23)+1,INT(({D('p_rank_py')}-70)/22)+4)",
         "hl_group_row": f"=IF({D('p_rank')}<=69,INT(({D('p_rank')}-1)/23)+1,INT(({D('p_rank')}-70)/22)+4)",
         "gcs_rank": f"=SUMPRODUCT(--(${DC['gcs']}${R1}:${DC['gcs']}${RN}<{D('gcs')}))+({D('gcs_ties')}+1)/2",
         "gcs_ties": f"=SUMPRODUCT(--(${DC['gcs']}${R1}:${DC['gcs']}${RN}={D('gcs')}))"}
    for j, n in enumerate(dcols, 1):
        if n in f:
            cl = ws.cell(r, j, f[n]); cl.font = F_LINK if n == "eta" else F_CALC
            if n in ("gcs", "gcs_z", "eta", "p_hat", "ll_term", "w", "gcs_rank"):
                cl.number_format = "0.0000"
        else:
            cl = ws.cell(r, j, vals[n]); cl.font = F_IN
# fix gcs_z (simple same-sheet ranges)
gr = f"${DC['gcs']}${R1}:${DC['gcs']}${RN}"
for r in range(R1, RN + 1):
    ws[f"{DC['gcs_z']}{r}"] = f"=({DC['gcs']}{r}-AVERAGE({gr}))/STDEVP({gr})"
    ws[f"{DC['gcs_z']}{r}"].font = F_CALC; ws[f"{DC['gcs_z']}{r}"].number_format = "0.0000"
ws.cell(1, len(dcols) + 2, "Legend: blue = data as coded/collected (final majority labels); black/green-header columns = Excel formulas. "
        "c01–c20 blank = control not applicable (its domain is absent); 1 = breached; 0 = applicable and held. "
        "cvss_recovered = 1 when the score was missing and was rebuilt from the CVSS 3.1 vector (see tab 02).").font = F_ST

# =============================================================== CODERS sheet
wc = wb.create_sheet("Coders")
ccols = ["case_id"] + [f"C1_d{j}" for j in range(1, 9)] + [f"C2_d{j}" for j in range(1, 9)] + \
        [f"LLM_d{j}" for j in range(1, 9)] + [f"Gold_d{j}" for j in range(1, 9)] + \
        [f"Maj_d{j}" for j in range(1, 9)] + ["Maj=Gold all 8", "Unanimous all 8", "C1_primary", "C2_primary",
                                             "LLM_primary", "Gold_primary", "C1_covered", "C2_covered", "LLM_covered"] + \
        [f"Votes_d{j}" for j in range(1, 9)] + ["Top votes", "Fallback domain"]
CC = {n: L(i + 1) for i, n in enumerate(ccols)}


def CR(n):
    return f"Coders!${CC[n]}${R1}:${CC[n]}${RN}"


for j, n in enumerate(ccols, 1):
    cl = wc.cell(1, j, n); cl.font = F_H
    cl.fill = PatternFill("solid", fgColor="375623") if n.startswith(("Maj", "Unan", "Votes", "Top", "Fallback")) else FILL_H
    cl.alignment = CENTER
    wc.column_dimensions[L(j)].width = 9
wc.column_dimensions["A"].width = 10
wc.freeze_panes = "B2"
src = {"C1": "coder1", "C2": "coder2", "LLM": "llm", "Gold": "gold"}
for i in range(N):
    r = i + 2
    wc.cell(r, 1, c.case_id[i]).font = F_IN
    for p, k in src.items():
        for j in range(1, 9):
            wc[f"{CC[f'{p}_d{j}']}{r}"] = int(codes[k][f"d{j}"][i]); wc[f"{CC[f'{p}_d{j}']}{r}"].font = F_IN
        wc[f"{CC[f'{p}_primary']}{r}"] = int(codes[k].primary_domain[i]); wc[f"{CC[f'{p}_primary']}{r}"].font = F_IN
        if p != "Gold":
            wc[f"{CC[f'{p}_covered']}{r}"] = int(codes[k].covered[i]); wc[f"{CC[f'{p}_covered']}{r}"].font = F_IN
    for j in range(1, 9):
        a, bb, l_ = (f"{CC[f'{p}_d{j}']}{r}" for p in ("C1", "C2", "LLM"))
        wc[f"{CC[f'Votes_d{j}']}{r}"] = f"={a}+{bb}+{l_}"
        V = f"{CC[f'Votes_d{j}']}{r}"
        wc[f"{CC[f'Maj_d{j}']}{r}"] = f"=IF({V}>=2,1,IF(AND({CC['Top votes']}{r}<2,{CC['Fallback domain']}{r}={j}),1,0))"
    wc[f"{CC['Top votes']}{r}"] = f"=MAX({CC['Votes_d1']}{r}:{CC['Votes_d8']}{r})"
    fb = "".join(f"IF({CC[f'Votes_d{d}']}{r}={CC['Top votes']}{r},{d}," for d in [4, 6, 2, 1, 8, 5, 3, 7]) + "0" + ")" * 8
    wc[f"{CC['Fallback domain']}{r}"] = "=" + fb
    wc[f"{CC['Maj=Gold all 8']}{r}"] = f"=IF(SUMPRODUCT(--({CC['Maj_d1']}{r}:{CC['Maj_d8']}{r}={CC['Gold_d1']}{r}:{CC['Gold_d8']}{r}))=8,1,0)"
    wc[f"{CC['Unanimous all 8']}{r}"] = (f"=IF(AND(SUMPRODUCT(--({CC['C1_d1']}{r}:{CC['C1_d8']}{r}={CC['C2_d1']}{r}:{CC['C2_d8']}{r}))=8,"
                                         f"SUMPRODUCT(--({CC['C2_d1']}{r}:{CC['C2_d8']}{r}={CC['LLM_d1']}{r}:{CC['LLM_d8']}{r}))=8),1,0)")

# =============================================================== TESTSET sheet
wt = wb.create_sheet("TestSet")
tcols = ["case_id", "y (high impact)", "p_M2 logistic", "p_M7 random forest", "pred_M2", "pred_M7", "rank_M2", "rank_M7"]
for j, n in enumerate(tcols, 1):
    cl = wt.cell(1, j, n); cl.font = F_H; cl.fill = FILL_H if j <= 4 else PatternFill("solid", fgColor="375623"); cl.alignment = CENTER
    wt.column_dimensions[L(j)].width = 15
NT = len(tp); T1, TN = 2, NT + 1
for i, rw in tp.iterrows():
    r = i + 2
    wt.cell(r, 1, rw.case_id).font = F_IN
    wt.cell(r, 2, int(rw.high_impact)).font = F_IN
    wt.cell(r, 3, float(rw.p_M2)).font = F_IN; wt.cell(r, 3).number_format = "0.0000"
    wt.cell(r, 4, float(rw.p_M7)).font = F_IN; wt.cell(r, 4).number_format = "0.0000"
wt.freeze_panes = "B2"
wt.cell(1, 10, "56 hold-out test cases (25% stratified split, seed 42). Probabilities come from the trained Python models "
        "(outputs/final/test_predictions.csv). Predicted class and ranks are Excel formulas; the threshold lives on tab 12.").font = F_ST

# =============================================================== continue RQ3 now Data exists
y_ = DR("high_impact"); ph = DR("p_hat"); ww = DR("w")
XR = {"b0": None, "b1": DR("gcs_z"), "b2": DR("x_eco"), "b3": DR("x_ndom"), "b4": DR("x_y26")}
rq3.section("B. Predictions and model fit (log-likelihood)")
rq3.row("rq3.n", "Number of cases used", f"=COUNT({y_})", "n", "Every one of the 223 incidents has a GCS, so all enter the model.", 223, 0, "0")
rq3.row("rq3.n1", "High-impact cases (events)", f"=SUM({y_})", "Σ y", "Cases with CVSS ≥ 7.0 (High or Critical) – the outcome = 1.", 156, 0, "0")
rq3.row("rq3.n0", "Low-impact cases (non-events)", "={rq3.n}-{rq3.n1}", "n − Σ y", "The smaller outcome group (67). With 4 predictors this gives 67/4 ≈ 16.8 events per predictor, above the usual 10-per-predictor rule.", 67, 0, "0")
rq3.row("rq3.ll", "Log-likelihood of Model 2 (LL₁)", f"=SUM({DR('ll_term')})",
        "LL = Σ [ y·ln p̂ + (1−y)·ln(1−p̂) ]",
        "For each case Data!p_hat is the model's predicted probability of high impact (1/(1+e^−η)). We score how probable the observed outcome was under the model and add the logs. Closer to 0 = better fit.",
        None, None, "0.000")
rq3.row("rq3.pbar", "Overall share of high impact", "={rq3.n1}/{rq3.n}", "ȳ = Σy / n", "The null (intercept-only) model predicts this same probability (about 70%) for everyone.", S["eda"]["hi_rate"], 0.001, "0.000")
rq3.row("rq3.ll0", "Log-likelihood of the null model (LL₀)", "={rq3.n1}*LN({rq3.pbar})+{rq3.n0}*LN(1-{rq3.pbar})",
        "LL₀ = n₁·ln ȳ + n₀·ln(1−ȳ)", "How well we could do with no predictors at all – the baseline to beat.", None, None, "0.000")
rq3.row("rq3.lr", "Likelihood-ratio (LR) chi-square", "=2*({rq3.ll}-{rq3.ll0})", "LR = 2(LL₁ − LL₀)",
        "Twice the improvement in log-likelihood. If the predictors were useless this would follow a chi-square with 4 df (one per predictor).", round(S["rq3"]["lr"], 2), 0.01, "0.00", key_row=True)
rq3.row("rq3.lrp", "p-value of the LR test", "=CHIDIST({rq3.lr},4)", "p = P(χ²₄ ≥ LR)",
        "Probability of an improvement this large by chance. It is about 0.000002, so the model as a whole is clearly better than guessing the average.", S["rq3"]["lr_p"], 1e-6, "0.0000000")
rq3.row("rq3.mcf", "McFadden pseudo-R²", "=1-{rq3.ll}/{rq3.ll0}", "R²_McF = 1 − LL₁/LL₀",
        "Share of the 'null' log-likelihood that the model removes. Values of 0.1–0.2 are normal for logistic models; 0.2–0.4 is considered an excellent fit.", round(S["rq3"]["mcfadden"], 3), 0.001, "0.000", key_row=True)
rq3.section("C. Proof that the typed coefficients are the maximum (score equations)")
for i, bn in enumerate(BN):
    xr = XR[bn]
    form = f"=SUMPRODUCT({y_}-{ph})" if xr is None else f"=SUMPRODUCT(({y_}-{ph})*{xr})"
    rq3.row(None, f"Score (gradient) for {bn}", form, "Σ (y − p̂)·x",
            "At the maximum-likelihood solution the slope of the log-likelihood is zero in every direction, so each of these sums must be ~0. "
            "If you change a blue coefficient by hand, these move away from 0 and LL₁ above gets worse – a hands-on way to see what 'maximum likelihood' means." if i == 0 else
            "Must also be ~0 (any value within ±0.01 is rounding from the 4-decimal coefficients).", 0, 0.05, "0.0000")
rq3.section("D. Standard errors from the information matrix  I = Xᵀ W X,  W = p̂(1−p̂)")
rq3.note("Each cell of the 5×5 grid is Σ w·xⱼ·xₖ over the 223 cases (Data!w = p̂(1−p̂)). The inverse of this matrix (MINVERSE, an array formula) is the covariance matrix of the coefficients; "
         "the square roots of its diagonal are the standard errors. This is exactly what statistical software does after fitting.")
rs = rq3.r
hdr = [""] + BN
first, last = rq3.table(hdr, [[bn] + [
    (f"=SUM({ww})" if XR[a] is None and XR[bb] is None else
     f"=SUMPRODUCT({ww},{XR[bb]})" if XR[a] is None else
     f"=SUMPRODUCT({ww},{XR[a]})" if XR[bb] is None else
     f"=SUMPRODUCT({ww},{XR[a]},{XR[bb]})") for bb in BN] for a, bn in zip(BN, BN)],
    fmts=[None] + ["0.000"] * 5)
info = f"$C${first}:$G${last}"
rq3.note("Inverse of the information matrix = variance–covariance matrix of b (array formula =MINVERSE of the grid above):")
first2, last2 = rq3.table(hdr, [[bn] + [None] * 5 for bn in BN], fmts=[None] + ["0.00000"] * 5)
rq3.ws[f"C{first2}"] = ArrayFormula(f"C{first2}:G{last2}", f"=MINVERSE({info})")
for rr in range(first2, last2 + 1):
    for cc_ in "CDEFG":
        rq3.ws[f"{cc_}{rr}"].number_format = "0.00000"; rq3.ws[f"{cc_}{rr}"].border = BOX
rq3.section("E. Wald tests, odds ratios and 95% confidence intervals (per term)")
rows = []
for i, (bn, tm) in enumerate(zip(BN, TERMS)):
    diag = f"{'CDEFG'[i]}{first2 + i}"
    rows.append([tm, f"={{rq3.{bn}}}", f"=SQRT({diag})", "=C{rr}/D{rr}", "=2*(1-NORMSDIST(ABS(E{rr})))",
                 "=EXP(C{rr})", "=EXP(C{rr}-NORMSINV(0.975)*D{rr})", "=EXP(C{rr}+NORMSINV(0.975)*D{rr})",
                 float(lg.OR[i])])
f3, l3 = rq3.table(["Term", "b", "SE = √diag", "z = b/SE", "p (two-sided)", "Odds ratio = eᵇ", "OR 95% low", "OR 95% high", "Report OR"],
                   rows, fmts=[None, "0.0000", "0.0000", "0.000", "0.0000", "0.000", "0.000", "0.000", "0.000"],
                   kinds=["text", "link", "calc", "calc", "calc", "calc", "calc", "calc", "input"])
for i, bn in enumerate(BN):
    REG[f"rq3.se{i}"] = (rq3.name, f"$D${f3 + i}")
    REG[f"rq3.or{i}"] = (rq3.name, f"$G${f3 + i}")
    REG[f"rq3.p{i}"] = (rq3.name, f"$F${f3 + i}")
rq3.row(None, "Key result: odds ratio for GCS (per SD)", f"=$G${f3 + 1}", "OR = e^b₁",
        "Each one-standard-deviation rise in GCS multiplies the odds of high impact by about 1.34 (34% higher odds). Because the 95% CI (0.99 to 1.81) just includes 1 and p ≈ .057, "
        "the GCS effect is positive but not significant at .05 – so H₀3 is not rejected. The number of domains (OR ≈ 2.28, p < .001) is the strong predictor.",
        float(lg.OR[1]), 0.001, "0.000", key_row=True)
rq3.row(None, "p-value for GCS", f"=$F${f3 + 1}", "p = 2[1 − Φ(|z|)]", "Wald test: z = b/SE compared with the standard normal curve.", float(lg.p[1]), 0.001, "0.0000")
rq3.row(None, "SE for GCS", f"=$D${f3 + 1}", "SE = √[(XᵀWX)⁻¹]₁₁", "Uncertainty of b₁, read off the inverse matrix diagonal.", float(lg.SE[1]), 0.001, "0.0000")
rq3.row(None, "Product-clustered SE for GCS (robustness)", float(lg.cluster_SE[1]), "Sandwich estimator by product",
        "Typed from Python. Incidents from the same product may be correlated, so we re-estimated SEs clustering by product. SE barely changes (0.155 vs 0.154), so the conclusion is the same.",
        float(lg.cluster_SE[1]), 0.001, "0.0000", kind="input")
rq3.section("F. Worked prediction for one example incident")
rq3.row("rq3.ex_gz", "Example: GCS z-score (editable)", 1.0, "z", "Type any value: e.g. 1 = one SD above the average GCS.", None, None, "0.00", kind="input")
rq3.row("rq3.ex_eco", "Example: ecosystem component? (1/0)", 0, "x₂", "1 if plugin/extension/MCP server.", None, None, "0", kind="input")
rq3.row("rq3.ex_nd", "Example: number of domains", 3, "x₃", "How many ACEG domains are breached.", None, None, "0", kind="input")
rq3.row("rq3.ex_y", "Example: published in 2026? (1/0)", 1, "x₄", "", None, None, "0", kind="input")
rq3.row("rq3.ex_eta", "Linear predictor η (log-odds)", "={rq3.b0}+{rq3.b1}*{rq3.ex_gz}+{rq3.b2}*{rq3.ex_eco}+{rq3.b3}*{rq3.ex_nd}+{rq3.b4}*{rq3.ex_y}",
        "η = b₀ + Σ bⱼxⱼ", "Add up the coefficients times the example's values.", None, None, "0.000")
rq3.row(None, "Predicted probability of high impact", "=1/(1+EXP(-{rq3.ex_eta}))", "p = 1 / (1 + e^−η)",
        "The logistic (S-shaped) function turns log-odds into a probability between 0 and 1.", None, None, "0.0%")
rq3.section("G. Multicollinearity – variance inflation factors (VIF)")
pairs_v = [("GCS z", "gcs_z", "x_eco", "x_y26"), ("Ecosystem", "x_eco", "x_ndom", "x_gz2"),
           ("Number of domains", "x_ndom", "x_y26", "x_eco2"), ("Published 2026", "x_y26", "x_gz2", "x_ndom2")]
for k, (nm, yv, a, z) in enumerate(pairs_v):
    xr = f"Data!${DC[a]}${R1}:${DC[z]}${RN}"
    rq3.row(None, f"VIF – {nm}", f"=1/(1-INDEX(LINEST({DR(yv)},{xr},TRUE,TRUE),3,1))", "VIF = 1 / (1 − R²ⱼ)",
            "Regress this predictor on the other three (LINEST), take R², and invert 1−R². VIF near 1 means the predictor carries its own information; above 5–10 would be a problem. All four are ≈1.0–1.1."
            if k == 0 else "Same recipe (the Data sheet repeats three columns so the 'other three' are always side by side for LINEST).",
            round(S["rq3"]["vif"][k], 3), 0.002, "0.000")
rq3.row(None, "Box–Tidwell linearity test p-value", S["rq3"]["box_tidwell_p"], "Wald p for GCS·ln(GCS) term",
        "Typed from Python. Checks that GCS relates to the log-odds in a straight line. p = .40 > .05, so linearity holds.", round(S["rq3"]["box_tidwell_p"], 3), 0.001, "0.000", kind="input")

# =============================================================== 10 Hosmer–Lemeshow
hl = Calc("10_RQ3_HosmerLemeshow", "RQ3 – Hosmer–Lemeshow goodness-of-fit test",
          "Sort the 223 cases by predicted probability (Data!p_rank_py = the sort order numpy used, typed in so the result reproduces the report), cut them into 10 groups of near-equal size (23,23,23,22,…,22 – the same split Python's array_split uses), "
          "then compare how many high-impact cases we observed in each group with how many the model expected.",
          "Section 4 Results – RQ3 model diagnostics")
gcol = DR("hl_group")
rows = [[g, f"=COUNTIF({gcol},B{{rr}})".replace("B{{rr}}", "B{rr}"), f"=SUMIF({gcol},B{{rr}},{y_})".replace("B{{rr}}", "B{rr}"),
         f"=SUMIF({gcol},B{{rr}},{ph})".replace("B{{rr}}", "B{rr}"), "=C{rr}-D{rr}", "=C{rr}-E{rr}",
         "=(D{rr}-E{rr})^2/(E{rr}*(1-E{rr}/C{rr}))"] for g in range(1, 11)]
f, l_ = hl.table(["Group (decile)", "n in group", "Observed high impact (O)", "Expected = Σ p̂ (E)", "Observed low impact", "Expected low impact", "(O−E)² / [E(1−E/n)]"],
                 rows, fmts=["0", "0", "0", "0.00", "0", "0.00", "0.000"], kinds=["input", "calc", "calc", "calc", "calc", "calc", "calc"])
hl.row("hl.stat", "Hosmer–Lemeshow statistic", f"=SUM(H{f}:H{l_})", "HL = Σ (O−E)² / [E(1−E/n)]",
       "Add up the ten mismatches. Small = the predicted probabilities line up with what actually happened.", round(S["rq3"]["hl"][0], 2), 0.05, "0.00", key_row=True)
hl.row("hl.df", "Degrees of freedom", 8, "df = groups − 2 = 10 − 2", "Convention for the HL test.", 8, 0, "0", kind="input")
hl.row(None, "p-value", "=CHIDIST({hl.stat},{hl.df})", "p = P(χ²₈ ≥ HL)",
       "p ≈ .62 is far above .05, so there is no evidence of poor calibration – the model fits.", round(S["rq3"]["hl"][2], 3), 0.01, "0.000")
hl.section("Same test, but breaking ties by Excel row order instead of numpy's sort order")
rows = [[g, f"=COUNTIF({DR('hl_group_row')},B{{rr}})".replace("{{rr}}", "{rr}"), f"=SUMIF({DR('hl_group_row')},B{{rr}},{y_})".replace("{{rr}}", "{rr}"),
         f"=SUMIF({DR('hl_group_row')},B{{rr}},{ph})".replace("{{rr}}", "{rr}"), "=(D{rr}-E{rr})^2/(E{rr}*(1-E{rr}/C{rr}))"] for g in range(1, 11)]
f2, l2 = hl.table(["Group", "n", "O", "E", "Contribution"], rows, fmts=["0", "0", "0", "0.00", "0.000"], kinds=["input", "calc", "calc", "calc", "calc"])
hl.row("hl.stat2", "HL statistic (row-order ties)", f"=SUM(F{f2}:F{l2})", "same formula", "Only 4 predictors, three of them whole numbers, so many incidents share an identical p̂ (164 duplicates). Which tied cases land in which decile is arbitrary, and here it moves HL from 6.2 to about 7.6.", None, None, "0.00")
hl.row(None, "p-value (row-order ties)", "=CHIDIST({hl.stat2},8)", "", "Still well above .05 – the 'good fit' conclusion is robust to how ties are split. This is a known weakness of the HL test with discrete predictors and why it is read alongside McFadden R² and AUC.", None, None, "0.000")


# =============================================================== 11 Mann–Whitney
mw = Calc("11_RQ3_MannWhitney", "RQ3 – Mann–Whitney U test: are GCS values higher in high-impact incidents?",
          "A rank-based (non-parametric) companion to the logistic model. GCS is very skewed (skew ≈ −2.3), so we compare the ranks rather than the means. "
          "All 223 GCS values are ranked together (ties share the average rank; Data!gcs_rank).", "Section 4 Results – RQ3 robustness check")
gs = DR("gcs"); grk = DR("gcs_rank"); gt = DR("gcs_ties")
mw.row("mw.n1", "n₁ – high-impact cases", f"=COUNTIF({y_},1)", "n₁", "", 156, 0, "0")
mw.row("mw.n0", "n₀ – low-impact cases", f"=COUNTIF({y_},0)", "n₀", "", 67, 0, "0")
mw.row(None, "Mean GCS – high impact", f"=AVERAGEIF({y_},1,{gs})", "", "Descriptive: high-impact incidents score a little higher on governance compliance on average.", round(S["rq3"]["gcs_mean_hi"], 2), 0.01, "0.00")
mw.row(None, "Mean GCS – low impact", f"=AVERAGEIF({y_},0,{gs})", "", "", round(S["rq3"]["gcs_mean_lo"], 2), 0.01, "0.00")
mw.row("mw.R1", "Sum of ranks of the high-impact group", f"=SUMIF({y_},1,{grk})", "R₁ = Σ ranks (group 1)",
       "If GCS had nothing to do with impact, each group's average rank would be ~112 (the middle of 1…223).", None, None, "0.0")
mw.row("mw.U", "U statistic", "={mw.R1}-{mw.n1}*({mw.n1}+1)/2", "U = R₁ − n₁(n₁+1)/2",
       "Counts how many (high, low) pairs have the high-impact case ranked above the low-impact case (ties count ½).", S["rq3"]["mw_u"], 0.5, "0", key_row=True)
mw.row("mw.mu", "Expected U if no difference", "={mw.n1}*{mw.n0}/2", "μ_U = n₁n₀ / 2", "Half of all 156×67 = 10,452 pairs.", None, None, "0.0")
mw.row("mw.tie", "Tie correction term", f"=SUMPRODUCT({gt}^2-1)", "Σ_groups (t³ − t)",
       "Many incidents share the same GCS (e.g. exactly 50 or 66.7). Each tied case contributes t²−1, which summed over the t members of a tie group gives t³−t.", None, None, "0")
mw.row("mw.N", "Total N", "={mw.n1}+{mw.n0}", "N = n₁ + n₀", "", 223, 0, "0")
mw.row("mw.sd", "Standard deviation of U (tie-corrected)", "=SQRT({mw.n1}*{mw.n0}/12*(({mw.N}+1)-{mw.tie}/({mw.N}*({mw.N}-1))))",
       "σ_U = √{ n₁n₀/12 · [(N+1) − Σ(t³−t)/(N(N−1))] }", "Ties reduce the spread of possible U values, so σ is shrunk slightly.", None, None, "0.00")
mw.row("mw.z", "z (with continuity correction 0.5)", "=(ABS({mw.U}-{mw.mu})-0.5)/{mw.sd}", "z = (|U − μ| − 0.5) / σ_U",
       "How many standard deviations U is from what we'd expect by chance. The 0.5 corrects for using a smooth curve on whole-number counts.", None, None, "0.000")
mw.row(None, "p-value (two-sided)", "=2*(1-NORMSDIST({mw.z}))", "p = 2[1 − Φ(z)]",
       "p ≈ .009 < .05: high-impact incidents do have higher GCS ranks. Together with the logistic OR of 1.34 (p = .057), the evidence for H3 is suggestive but not conclusive once other predictors are controlled.",
       round(S["rq3"]["mw_p"], 4), 0.0005, "0.0000", key_row=True)
mw.row(None, "Effect size: probability of superiority", "={mw.U}/({mw.n1}*{mw.n0})", "A = U / (n₁n₀)",
       "Chance that a randomly picked high-impact incident has a higher GCS than a randomly picked low-impact one (0.5 = no difference).", None, None, "0.000")

# =============================================================== 01 GCS worked example
g = Calc("01_GCS_WorkedExample", "Governance Compliance Score (GCS) – how one incident is scored",
         "GCS = 100 × (applicable controls − breached controls) / applicable controls. A control is 'applicable' only when its domain is present in the incident. "
         "Change the blue case ID to see any incident scored live from the Data tab.", "Section 3 Methodology – Measures (GCS); Section 4 – RQ3")
g.row("g.case", "Case ID (editable)", "CA-018", "input", "Type any case ID from CA-001 to CA-223.", None, None, "@", kind="input")
g.row("g.row", "Row of that case in Data", f"=MATCH({{g.case}},Data!$A${R1}:$A${RN},0)", "MATCH", "Finds which data row holds this incident.", None, None, "0")
rows = []
dom_of = {}
for j, cs in LINK.items():
    for k in cs:
        dom_of[k] = j
for k in range(1, 21):
    j = dom_of[k]
    rows.append([f"C{k:02d}", f"D{j}", f"=INDEX(Data!${DC[f'd{j}']}${R1}:${DC[f'd{j}']}${RN},{{g.row}})",
                 f'=IF(INDEX(Data!${DC[f"c{k:02d}"]}${R1}:${DC[f"c{k:02d}"]}${RN},{{g.row}})="","NA",INDEX(Data!${DC[f"c{k:02d}"]}${R1}:${DC[f"c{k:02d}"]}${RN},{{g.row}}))',
                 "=D{rr}", '=IF(AND(D{rr}=1,E{rr}=1),1,0)'])
g.note("Step-by-step control table: for each of the 20 controls, is its domain present (applicable = 1) and was it breached (1) or held (0)?")
f, l_ = g.table(["Control", "Owning domain", "Domain present?", "Coded value (NA / 0 / 1)", "Applicable (1/0)", "Breached (1/0)"],
                rows, fmts=[None, None, "0", "0", "0", "0"], kinds=["text", "text", "link", "link", "calc", "calc"])
g.row("g.app", "Applicable controls", f"=SUM(F{f}:F{l_})", "A = Σ applicable",
      "Each present domain brings all of its controls: D1, D6, D7, D8 bring 3 each; D2–D5 bring 2 each.", None, None, "0")
g.row("g.br", "Breached controls", f"=SUM(G{f}:G{l_})", "B = Σ breached", "Controls the coders judged to have failed in this incident.", None, None, "0")
g.row("g.gcs", "GCS", '=IF({g.app}=0,"",100*({g.app}-{g.br})/{g.app})', "GCS = 100·(A − B)/A",
      "Share of applicable controls that held, in %. 100 = every applicable safeguard held; 0 = every applicable safeguard failed.", None, None, "0.00", key_row=True)
g.row(None, "Same value on the Data tab", f"=INDEX({DR('gcs')},{{g.row}})", "Data!gcs", "Cross-check against the column the analysis uses.", None, None, "0.00", kind="link")
REG["tmp"] = (g.name, f"$C${g.r - 1}")
g.ws.cell(g.r - 1, 7, f"={ref('g.gcs', g.name)}").number_format = "0.00"
g.ws.cell(g.r - 1, 8, f'=IF(ABS(C{g.r - 1}-G{g.r - 1})<0.001,"✓ matches","check")').font = F_OK
g.section("Dataset-wide GCS facts")
g.row(None, "Mean GCS across 223 incidents", f"=AVERAGE({gs})", "x̄", "Average governance compliance: roughly half the applicable controls held.", 52.79, 0.01, "0.00")
g.row(None, "Incidents with GCS = 0 (every applicable control breached)", f"=COUNTIF({gs},0)", "count", "", None, None, "0")
g.row(None, "Maximum GCS observed", f"=MAX({gs})", "max", "Max is 66.67: no incident had all its applicable controls hold – by construction each incident breaches at least one control.", 66.67, 0.01, "0.00")

# =============================================================== 02 CVSS recovery
cv = Calc("02_CVSS_Recovery", "Data cleaning – rebuilding a missing CVSS 3.1 base score from its vector",
          "31 incidents had no published base score; 24 of them carried a CVSS 3.1 vector, so the score was recomputed with the official FIRST CVSS v3.1 equations. "
          "Edit the blue vector to try any other.", "Section 3 Methodology – Data cleaning (Table: cleaning log)")
cv.row("cv.v", "CVSS 3.1 vector (editable) – case CA-056", "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:L", "input",
       "Each letter pair is one metric: Attack Vector, Attack Complexity, Privileges Required, User Interaction, Scope, then Confidentiality, Integrity, Availability impact.", None, None, "@", kind="input")
mets = [("AV", "Attack vector", {"N": .85, "A": .62, "L": .55, "P": .2}), ("AC", "Attack complexity", {"L": .77, "H": .44}),
        ("UI", "User interaction", {"N": .85, "R": .62}), ("C", "Confidentiality impact", {"H": .56, "L": .22, "N": 0}),
        ("I", "Integrity impact", {"H": .56, "L": .22, "N": 0}), ("A", "Availability impact", {"H": .56, "L": .22, "N": 0})]
cv.row("cv.S", "Scope letter (U = unchanged, C = changed)", '=MID({cv.v},SEARCH("/S:",{cv.v})+3,1)', "parse", "Changed scope means the attack can break out into other components – it raises the score.", None, None, "@")
cv.row("cv.PRl", "Privileges required letter", '=MID({cv.v},SEARCH("/PR:",{cv.v})+4,1)', "parse", "", None, None, "@")
for code, nm, wts in mets:
    key = f"cv.{code}"
    cv.row(key + "l", f"{nm} letter", f'=MID({{cv.v}},SEARCH("/{code}:",{{cv.v}})+{len(code) + 2},1)', "parse", "Read the letter after the metric's code.", None, None, "@")
    ifs = "".join(f'IF({{{key}l}}="{k}",{v},' for k, v in wts.items()) + "0" + ")" * len(wts)
    cv.row(key, f"{nm} weight", "=" + ifs, " / ".join(f"{k}={v}" for k, v in wts.items()), "Look up the official weight for that letter.", None, None, "0.00")
cv.row("cv.PR", "Privileges required weight", '=IF({cv.PRl}="N",0.85,IF({cv.PRl}="L",IF({cv.S}="C",0.68,0.62),IF({cv.S}="C",0.5,0.27)))',
       "N=.85; L=.62 (.68 if S:C); H=.27 (.50 if S:C)", "Privileges weigh more when scope is changed.", None, None, "0.00")
cv.row("cv.iss", "Impact sub-score (ISS)", "=1-(1-{cv.C})*(1-{cv.I})*(1-{cv.A})", "ISS = 1 − (1−C)(1−I)(1−A)",
       "Combines the three impact metrics: the chance that at least one of confidentiality, integrity or availability is hit.", None, None, "0.0000")
cv.row("cv.imp", "Impact", '=IF({cv.S}="U",6.42*{cv.iss},7.52*({cv.iss}-0.029)-3.25*({cv.iss}-0.02)^15)',
       "S:U → 6.42·ISS;  S:C → 7.52(ISS−.029) − 3.25(ISS−.02)¹⁵", "Scales impact onto the 0–10 range.", None, None, "0.0000")
cv.row("cv.exp", "Exploitability", "=8.22*{cv.AV}*{cv.AC}*{cv.PR}*{cv.UI}", "E = 8.22·AV·AC·PR·UI", "How easy the attack is to carry out.", None, None, "0.0000")
cv.row("cv.score", "Base score", '=IF({cv.imp}<=0,0,IF({cv.S}="U",ROUNDUP(ROUND(MIN({cv.imp}+{cv.exp},10),5),1),ROUNDUP(ROUND(MIN(1.08*({cv.imp}+{cv.exp}),10),5),1)))',
       "S:U → ⌈min(I+E,10)⌉;  S:C → ⌈min(1.08(I+E),10)⌉ (round up to 1 decimal)", "The final 0–10 score. CA-056 comes out 7.4 → High, which matches its published severity band.",
       base_score("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:L"), 0.001, "0.0", key_row=True)
cv.row(None, "Severity band", '=IF({cv.score}=0,"NONE",IF({cv.score}<4,"LOW",IF({cv.score}<7,"MEDIUM",IF({cv.score}<9,"HIGH","CRITICAL"))))',
       "0 / 0.1–3.9 / 4–6.9 / 7–8.9 / 9–10", "High impact (the RQ3 outcome) = High or Critical, i.e. score ≥ 7.0.", None, None, "@")
cv.section("Cleaning log totals")
cv.row(None, "Scores recovered from vectors (whole dataset)", f"=SUM({DR('cvss_recovered')})", "Σ flag", "All 24 recovered scores landed in the same band as the published severity label.", S["cleaning"]["recovered"], 0, "0")
cv.row(None, "Scores still missing (no 3.1 vector)", f"=COUNTBLANK({DR('cvss_score')})", "count blanks", "7 cases carry only a CVSS 4.0 vector or none; they keep their published severity band.", S["cleaning"]["left_missing"], 0, "0")

# =============================================================== 03 Descriptives
de = Calc("03_EDA_Descriptives", "Exploratory data analysis – descriptive statistics and outliers",
          "Centre, spread, shape and outliers for the key numeric variables (Table: numeric summary).", "Section 4 Results – Exploratory data analysis")
cs_ = DR("cvss_score")
eda = T("eda_numeric_summary").set_index("Unnamed: 0")
for nm, rng, lab in [("cvss", cs_, "CVSS base score"), ("gcs", gs, "Governance Compliance Score (%)"), ("nd", DR("n_domains"), "Domains present (final labels)")]:
    e = eda.loc[lab]
    de.section(lab)
    de.row(f"de.{nm}.n", "Count (non-missing)", f"=COUNT({rng})", "n", "How many cases have a value.", e["count"], 0, "0")
    de.row(f"de.{nm}.mean", "Mean", f"=AVERAGE({rng})", "x̄ = Σx / n", "The arithmetic average.", e["mean"], 0.006, "0.00")
    de.row(f"de.{nm}.med", "Median", f"=MEDIAN({rng})", "middle value", "Half the cases are below, half above. Robust to outliers.", e["50%"], 0.006, "0.00")
    de.row(f"de.{nm}.sd", "Standard deviation", f"=STDEV({rng})", "s = √[Σ(x−x̄)²/(n−1)]", "Typical distance of a case from the mean.", e["std"], 0.006, "0.00")
    de.row(f"de.{nm}.q1", "Q1 (25th percentile)", f"=QUARTILE({rng},1)", "linear interpolation", "A quarter of cases fall below this.", e["25%"], 0.006, "0.00")
    de.row(f"de.{nm}.q3", "Q3 (75th percentile)", f"=QUARTILE({rng},3)", "", "Three quarters fall below this.", e["75%"], 0.006, "0.00")
    de.row(f"de.{nm}.iqr", "Interquartile range (IQR)", f"={{de.{nm}.q3}}-{{de.{nm}.q1}}", "IQR = Q3 − Q1", "Spread of the middle half of the data.", None, None, "0.00")
    de.row(f"de.{nm}.lf", "Lower Tukey fence", f"={{de.{nm}.q1}}-1.5*{{de.{nm}.iqr}}", "Q1 − 1.5·IQR", "Values below this are flagged as outliers.", None, None, "0.00")
    de.row(f"de.{nm}.uf", "Upper Tukey fence", f"={{de.{nm}.q3}}+1.5*{{de.{nm}.iqr}}", "Q3 + 1.5·IQR", "Values above this are flagged as outliers.", None, None, "0.00")
    de.row(None, "Outliers (outside the fences)", f'=COUNTIF({rng},"<"&{{de.{nm}.lf}})+COUNTIF({rng},">"&{{de.{nm}.uf}})', "count", "Outliers were reviewed and kept – they are genuine incidents, not data errors.", None, None, "0")
    de.row(None, "Skewness", f"=SKEW({rng})", "adjusted Fisher–Pearson", "Negative = long tail to the left (a few very low values). GCS is strongly left-skewed – one reason we also use the rank-based Mann–Whitney test.", e["skew"], 0.006, "0.00")
de.section("Outcome and category counts")
de.row(None, "High-impact share", f"=AVERAGE({y_})", "Σy / n", "70% of incidents are High or Critical – this is the class balance for the models (and the M0 baseline accuracy on the training split).", S["eda"]["hi_rate"], 0.001, "0.0%")
for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
    de.row(None, f"Severity = {sev}", f'=COUNTIF({DR("severity")},"{sev}")', "COUNTIF", "", S["eda"]["severity"][sev], 0, "0")
de.row(None, "Ecosystem components", f"=SUM({DR('ecosystem')})", "Σ", "Plugins, extensions, MCP servers etc.", S["eda"]["ecosystem"], 0, "0")
de.row(None, "Published in 2026", f"=SUM({DR('year_2026')})", "Σ", "", S["eda"]["years"]["2026"], 0, "0")

# =============================================================== crosstab helper
def crosstab(calc, key, rowcats, rowrange, colvals, colrange, collabels, rowlabels=None, report=None):
    k = len(colvals)
    hdr = ["Category"] + [f"Observed: {cl}" for cl in collabels] + ["Row total"]
    rows = []
    for i, rc_ in enumerate(rowcats):
        cells = [rowlabels[i] if rowlabels else rc_]
        for v in colvals:
            vv = f'"{v}"' if isinstance(v, str) else v
            cells.append(f'=COUNTIFS({rowrange},"{rc_}",{colrange},{vv})')
        cells.append("=SUM(" + f"C{{rr}}:{L(2 + k)}{{rr}}" + ")")
        rows.append(cells)
    calc.note("Step 1 – Observed counts (COUNTIFS on the Data tab):")
    f, l_ = calc.table(hdr, rows, fmts=[None] + ["0"] * (k + 1), kinds=["text"] + ["calc"] * (k + 1))
    tr = calc.r
    # totals row
    ws_ = calc.ws
    ws_.cell(tr - 1, 2, "Column total").font = F_TXT
    for j in range(k + 1):
        cl = ws_.cell(tr - 1, 3 + j, f"=SUM({L(3 + j)}{f}:{L(3 + j)}{l_})"); cl.font = F_CALC; cl.border = BOX
    tot = f"${L(3 + k)}${tr - 1}"
    calc.r += 1
    calc.note("Step 2 – Expected counts if the two variables were unrelated: E = row total × column total ÷ grand total.")
    rows = [[rowlabels[i] if rowlabels else rc_] + [f"=${L(3 + k)}{f + i}*{L(3 + j)}${tr - 1}/{tot}" for j in range(k)] for i, rc_ in enumerate(rowcats)]
    fe, le = calc.table(["Category"] + [f"Expected: {cl}" for cl in collabels], rows, fmts=[None] + ["0.00"] * k)
    calc.note("Step 3 – Each cell's contribution (O − E)² / E, and the standardized residual (O − E)/√E (|value| > 2 would flag a cell that drives the result).")
    rows = [[rowlabels[i] if rowlabels else rc_] + [f"=({L(3 + j)}{f + i}-{L(3 + j)}{fe + i})^2/{L(3 + j)}{fe + i}" for j in range(k)] +
            [f"=({L(3 + j)}{f + i}-{L(3 + j)}{fe + i})/SQRT({L(3 + j)}{fe + i})" for j in range(k)] for i, rc_ in enumerate(rowcats)]
    fc, lc = calc.table(["Category"] + [f"(O−E)²/E: {cl}" for cl in collabels] + [f"Std residual: {cl}" for cl in collabels], rows,
                        fmts=[None] + ["0.000"] * (2 * k))
    calc.row(f"{key}.chi", "Pearson chi-square", f"=SUM(C{fc}:{L(2 + k)}{lc})", "χ² = Σ (O − E)² / E",
             "Add up every cell's contribution. Big = observed counts far from what independence predicts.", report.get("chi"), 0.005, "0.000", key_row=True)
    calc.row(f"{key}.df", "Degrees of freedom", f"=({len(rowcats)}-1)*({k}-1)", "df = (rows − 1)(columns − 1)", "", report.get("df"), 0, "0")
    calc.row(f"{key}.p", "p-value", f"=CHIDIST({{{key}.chi}},{{{key}.df}})", "p = P(χ²_df ≥ χ²)", report.get("pex", ""), report.get("p"), 0.001, "0.0000")
    calc.row(f"{key}.N", "Grand total N", f"={tot}", "N", "", report.get("N"), 0, "0")
    calc.row(f"{key}.V", "Cramér's V (effect size)", f"=SQRT({{{key}.chi}}/({{{key}.N}}*(MIN({len(rowcats)},{k})-1)))", "V = √[χ² / (N·(min(r,c) − 1))]",
             "Strength of association on a 0–1 scale (≈.1 small, ≈.3 medium, ≈.5 large).", report.get("V"), 0.002, "0.000", key_row=True)
    calc.row(None, "Smallest expected count", f"=MIN(C{fe}:{L(2 + k)}{le})", "min E", "Chi-square works best when expected counts are ≥ 5; small ones are why we add an exact/Monte Carlo check.", report.get("minE"), 0.01, "0.00")
    calc.row(None, "Cells with expected count < 5", f'=COUNTIF(C{fe}:{L(2 + k)}{le},"<5")', "count", "", report.get("nlt5"), 0, "0")
    return f, fe


# =============================================================== 04 EDA chi-square
ec = Calc("04_EDA_ChiSquare", "EDA – Chi-square test of association: CWE weakness group × high impact",
          "Does the type of software weakness (CWE group – today's triage practice) relate to whether an incident is high impact? This also motivates model M3.",
          "Section 4 Results – Exploratory data analysis (association table)")
ea = T("eda_association").set_index("Characteristic")
grps = [n for n, _ in CWE_GROUPS] + ["Other"]
crosstab(ec, "ec", grps, DR("cwe_group"), [1, 0], y_, ["High impact", "Not high"],
         report={"chi": round(ea.loc["CWE group", "chi2"], 2), "df": 7, "p": float(ea.loc["CWE group", "p"]) if "p" in ea.columns else None,
                 "pex": "A very small p: CWE group is strongly associated with impact – e.g. command/code injection is almost always high impact.",
                 "N": 223, "V": round(ea.loc["CWE group", "cramers_v"], 3), "minE": round(ea.loc["CWE group", "min_expected"], 2), "nlt5": None})
ec.section("Same recipe, 2×2 table: ecosystem component × high impact")
crosstab(ec, "ec2", ["ecosystem", "agent product"], DR("component_type"), [1, 0], y_, ["High impact", "Not high"],
         report={"chi": round(ea.loc["Ecosystem component", "chi2"], 3), "df": 1, "p": float(ea.loc["Ecosystem component", "p"]) if "p" in ea.columns else None,
                 "pex": "p ≈ .30: plugins/extensions are not more or less likely to be high impact than core products.",
                 "N": 223, "V": round(ea.loc["Ecosystem component", "cramers_v"], 3), "minE": round(ea.loc["Ecosystem component", "min_expected"], 2), "nlt5": 0})

# =============================================================== 05 Sample size
ss = Calc("05_SampleSize", "Sample size justification – RQ1 to RQ4 (α = .05, power = .80)",
          "Each research question has its own formula; the study needs the largest of the four. All 223 eligible incidents were coded, which exceeds every requirement.",
          "Section 3 Methodology – Sample size and power")
ss.row("ss.za", "Z for α = .05 two-sided", "=NORMSINV(0.975)", "z₁₋α/₂", "1.96: the cut-off that leaves 2.5% in each tail of the normal curve.", 1.96, 0.001, "0.0000")
ss.row("ss.zb", "Z for power = .80", "=NORMSINV(0.8)", "z₁₋β", "0.8416: gives an 80% chance of detecting a true effect.", 0.8416, 0.0001, "0.0000")
ss.section("RQ1 – estimate framework coverage within ±7 points")
ss.row("ss.p1", "Planning proportion p", 0.5, "p", "0.5 is the most conservative choice (largest p(1−p)).", None, None, "0.00", kind="input")
ss.row("ss.e1", "Margin of error e", 0.07, "e", "Width of the 95% CI on each side.", None, None, "0.00", kind="input")
ss.row("ss.n1", "Required n (RQ1)", "={ss.za}^2*{ss.p1}*(1-{ss.p1})/{ss.e1}^2", "n = z²·p(1−p)/e²", "≈ 196 incidents.", 196, 0.05, "0.00", key_row=True)
ss.row(None, "Achieved margin at N = 223", "={ss.za}*SQRT(0.25/223)", "e = z·√(0.25/N)", "With 223 cases the CI is ±6.6 points – tighter than planned.", 0.066, 0.001, "0.000")
ss.section("RQ2 – chi-square test of independence (Cohen's w = .25, df = 3)")
ss.row("ss.w", "Effect size w", 0.25, "w", "A small-to-medium effect (Cohen, 1988).", None, None, "0.00", kind="input")
ss.row("ss.df2", "Degrees of freedom", 3, "(4 families − 1)(2 − 1)", "", None, None, "0", kind="input")
ss.row("ss.crit", "Critical χ² at α = .05", "=CHIINV(0.05,{ss.df2})", "χ²₀.₉₅,₃", "Test statistic beyond which we reject H₀.", 7.815, 0.001, "0.000")
ss.row("ss.lam", "Non-centrality λ giving 80% power", 10.903, "solve P(χ²₃(λ) > 7.815) = .80",
       "Typed from Python (scipy ncx2 + root finder): Excel has no non-central chi-square function. The check below verifies it with the Patnaik approximation.", 10.903, 0.001, "0.000", kind="input")
ss.row("ss.n2", "Required n (RQ2)", "={ss.lam}/{ss.w}^2", "n = λ / w²", "≈ 175 incidents.", 174.44, 0.05, "0.00", key_row=True)
ss.row("ss.pc", "Patnaik check: scale c", "=({ss.df2}+2*{ss.lam})/({ss.df2}+{ss.lam})", "c = (k+2λ)/(k+λ)", "Approximates the non-central χ² by c × a central χ² with ν′ df.", None, None, "0.0000")
ss.row("ss.pn", "Patnaik check: df ν′", "=({ss.df2}+{ss.lam})^2/({ss.df2}+2*{ss.lam})", "ν′ = (k+λ)²/(k+2λ)", "", None, None, "0.0000")
ss.row(None, "Approximate power at λ = 10.903", "=1-GAMMADIST({ss.crit}/{ss.pc},{ss.pn}/2,2,TRUE)", "≈ P(χ²_ν′ > crit/c)", "≈ 0.80 – confirms λ.", 0.80, 0.01, "0.000")
ss.row(None, "Approximate achieved power at n = 221", "=1-GAMMADIST({ss.crit}/((3+2*221*{ss.w}^2)/(3+221*{ss.w}^2)),((3+221*{ss.w}^2)^2/(3+2*221*{ss.w}^2))/2,2,TRUE)",
       "λ = 221·w² = 13.81", "Power actually achieved for RQ2. The Patnaik shortcut slightly overstates it (≈0.90); the exact non-central value from Python is 0.892 – both are well above 0.80.", round(S["rq2"]["power_w25"], 3), 0.015, "0.000")
ss.section("RQ3 – logistic regression with a continuous predictor (Hsieh, Bloch & Larsen, 1998)")
ss.row("ss.P", "Event proportion P", 0.70, "P", "Share of high-impact incidents.", None, None, "0.00", kind="input")
ss.row("ss.beta", "Detectable log-odds per SD β*", 0.50, "|β*|", "Odds ratio 1.65 per SD (ln 1.65 ≈ 0.50).", None, None, "0.00", kind="input")
ss.row("ss.r2", "R² of GCS with other predictors", 0.20, "ρ²", "Inflates n to allow for correlated covariates.", None, None, "0.00", kind="input")
ss.row("ss.n3a", "Unadjusted n", "=({ss.za}+{ss.zb})^2/({ss.P}*(1-{ss.P})*{ss.beta}^2)", "n = (z₁₋α/₂ + z₁₋β)² / [P(1−P)β*²]", "", 149.50, 0.05, "0.00")
ss.row("ss.n3", "Required n (RQ3)", "={ss.n3a}/(1-{ss.r2})", "n / (1 − ρ²)", "≈ 187 incidents.", 186.88, 0.05, "0.00", key_row=True)
ss.row(None, "Events per predictor (achieved)", "=67/4", "min(events, non-events) / predictors", "16.8 ≥ 10 – enough for stable estimates.", 16.75, 0.01, "0.00")
ss.section("RQ4 – estimate LLM classification accuracy within ±6 points")
ss.row("ss.acc", "Planning accuracy", 0.80, "p", "", None, None, "0.00", kind="input")
ss.row("ss.e4", "Margin e", 0.06, "e", "", None, None, "0.00", kind="input")
ss.row("ss.n4", "Required n (RQ4)", "={ss.za}^2*{ss.acc}*(1-{ss.acc})/{ss.e4}^2", "n = z²·p(1−p)/e²", "≈ 171 incidents.", 170.74, 0.05, "0.00", key_row=True)
ss.section("Overall")
ss.row(None, "Required N = largest of the four (rounded up)", "=MAX(ROUNDUP({ss.n1},0),ROUNDUP({ss.n2},0),ROUNDUP({ss.n3},0),ROUNDUP({ss.n4},0))",
       "N = max ⌈nᵢ⌉", "196 needed; 223 coded. Every RQ is adequately powered.", 196, 0, "0", key_row=True)

# =============================================================== 06 RQ1 coverage
r1 = Calc("06_RQ1_Coverage", "RQ1 – Does ACEG cover at least 80% of real agentic-AI incidents?",
          "H₀1: coverage π ≤ .80   vs   H₁1: π > .80. 'Covered' = at least one ACEG domain applies to the incident (final majority labels).",
          "Section 4 Results – RQ1 (coverage and Wilson CI)")
cov = DR("covered")
r1.row("r1.k", "Covered incidents k", f"=SUM({cov})", "k = Σ covered", "Incidents that map to at least one domain.", 222, 0, "0")
r1.row("r1.n", "All incidents n", f"=COUNT({cov})", "n", "", 223, 0, "0")
r1.row("r1.p", "Observed coverage", "={r1.k}/{r1.n}", "p̂ = k/n", "99.6% of incidents are covered.", S["rq1"]["p"], 0.0005, "0.0%", key_row=True)
r1.row(None, "The one uncovered case", f"=INDEX(Data!$A${R1}:$A${RN},MATCH(0,{cov},0))", "lookup", "CA-121 – reviewed qualitatively in the Discussion.", None, None, "@")
r1.section("Wilson 95% confidence interval (better than p̂ ± 1.96·SE when p̂ is near 0 or 1)")
r1.row("r1.z", "z", "=NORMSINV(0.975)", "z = 1.96", "", None, None, "0.0000")
r1.row("r1.den", "Denominator", "=1+{r1.z}^2/{r1.n}", "1 + z²/n", "", None, None, "0.00000")
r1.row("r1.ctr", "Centre", "=({r1.p}+{r1.z}^2/(2*{r1.n}))/{r1.den}", "[p̂ + z²/(2n)] / den", "The Wilson interval is centred slightly toward 0.5 – a small built-in correction.", None, None, "0.00000")
r1.row("r1.hw", "Half-width", "={r1.z}*SQRT({r1.p}*(1-{r1.p})/{r1.n}+{r1.z}^2/(4*{r1.n}^2))/{r1.den}", "z·√[p̂(1−p̂)/n + z²/(4n²)] / den", "", None, None, "0.00000")
r1.row(None, "Lower 95% bound", "={r1.ctr}-{r1.hw}", "centre − half-width", "Even the lowest plausible coverage (97.5%) is far above the 80% benchmark.", S["rq1"]["lo"], 0.0005, "0.0%", key_row=True)
r1.row(None, "Upper 95% bound", "={r1.ctr}+{r1.hw}", "centre + half-width", "", S["rq1"]["hi"], 0.0005, "0.0%")
r1.section("Exact one-sided binomial test against π₀ = .80")
r1.row("r1.p0", "Benchmark π₀", 0.80, "π₀", "The coverage threshold set in the proposal.", None, None, "0.00", kind="input")
r1.row(None, "p-value = P(X ≥ 222 | n = 223, π = .80)", "=BINOMDIST({r1.k},{r1.n},{r1.p0},FALSE)+BINOMDIST({r1.n},{r1.n},{r1.p0},FALSE)",
       "Σₓ₌ₖⁿ C(n,x)·π₀ˣ(1−π₀)ⁿ⁻ˣ",
       "If true coverage were only 80%, the chance of seeing 222 or more covered out of 223 is about 1 in 10²⁰. We reject H₀1: ACEG covers well over 80%. "
       "(We add the two exact terms rather than 1 − CDF, which would lose all precision.)", S["rq1"]["binom_p"], 1e-21, "0.00E+00", key_row=True)
r1.section("Coverage by each coder (robustness)")
for p, nm in [("C1", "Coder 1 (human)"), ("C2", "Coder 2 (human)"), ("LLM", "LLM coder")]:
    key = {"C1": "coder1", "C2": "coder2", "LLM": "llm"}[p]
    r1.row(None, f"Coverage – {nm}", f"=AVERAGE({CR(p + '_covered')})", "mean(covered)", "Coverage is above 80% under every coder's labels." if p == "C1" else "",
           S["rq1"]["coverage_by_source"][key][1] / 100, 0.001, "0.0%")

# =============================================================== 07 RQ1 prevalence
pv = Calc("07_RQ1_Prevalence", "RQ1 – Domain prevalence, control breach rates and domain co-occurrence",
          "How often does each of the eight ACEG domains appear, and which controls fail most? Each prevalence gets its own Wilson 95% CI.",
          "Section 4 Results – RQ1 (domain prevalence table, control breach table, co-occurrence heat map)")
prev = T("rq1_domain_prevalence")
z = "NORMSINV(0.975)"
rows = []
for j in range(1, 9):
    rng = DR(f"d{j}")
    rows.append([DNAME[j], FAM[j], f"=SUM({rng})", f"=D{{rr}}/{N}",
                 f"=(E{{rr}}+{z}^2/(2*{N})-{z}*SQRT(E{{rr}}*(1-E{{rr}})/{N}+{z}^2/(4*{N}^2)))/(1+{z}^2/{N})",
                 f"=(E{{rr}}+{z}^2/(2*{N})+{z}*SQRT(E{{rr}}*(1-E{{rr}})/{N}+{z}^2/(4*{N}^2)))/(1+{z}^2/{N})",
                 f"=SUM({CR(f'C1_d{j}')})", f"=SUM({CR(f'C2_d{j}')})", f"=SUM({CR(f'LLM_d{j}')})",
                 float(prev.gold_pct[j - 1]) / 100, '=IF(ABS(E{rr}-K{rr})<0.0006,"✓","check")'])
rows = [[x.replace("{{rr}}", "{rr}") if isinstance(x, str) else x for x in rw] for rw in rows]
pv.note("Each row: count of incidents with the domain present (final labels), share, Wilson CI (same formula as tab 06), and the count under each coder.")
f, l_ = pv.table(["Domain", "Family", "n present", "Prevalence", "Wilson low", "Wilson high", "Coder 1 n", "Coder 2 n", "LLM n", "Report %", "Check"],
                 rows, fmts=[None, None, "0", "0.0%", "0.0%", "0.0%", "0", "0", "0", "0.0%", None],
                 kinds=["text", "text", "calc", "calc", "calc", "calc", "link", "link", "link", "input", "calc"])
pv.row(None, "Mean number of domains per incident", f"=AVERAGE({DR('n_domains')})", "Σ domains / n",
       "Incidents typically breach about two domains at once – governance failures cluster.", S["rq1"]["mean_domains"]["gold"], 0.001, "0.00")
pv.section("Control breach rates (C01–C20)")
cb = T("rq1_control_breaches")
rows = []
for k in range(1, 21):
    rng = DR(f"c{k:02d}")
    rows.append([f"C{k:02d}", f"D{dom_of[k]}", f"=COUNT({rng})", f"=COUNTIF({rng},1)", "=IF(D{rr}=0,\"\",E{rr}/D{rr})", f"=E{{rr}}/{N}".replace("{{rr}}", "{rr}"),
                 float(cb.breach_rate_applicable[k - 1]), '=IF(F{rr}="","",IF(ABS(F{rr}-H{rr})<0.001,"✓","check"))'])
pv.note("Applicable = incidents where the control's domain is present (non-blank cell). Breach rate among applicable = breached ÷ applicable.")
pv.table(["Control", "Domain", "Applicable", "Breached", "Breach rate (applicable)", "Share of all 223", "Report rate", "Check"], rows,
         fmts=[None, None, "0", "0", "0.0%", "0.0%", "0.0%", None], kinds=["text", "text", "calc", "calc", "calc", "calc", "input", "calc"])
pv.section("Domain co-occurrence matrix (how many incidents have both domains)")
rows = []
for a in range(1, 9):
    rows.append([f"D{a}"] + [f"=SUMPRODUCT({DR(f'd{a}')},{DR(f'd{bb}')})" for bb in range(1, 9)])
pv.note("Cell (row Dᵢ, column Dⱼ) = Σ dᵢ·dⱼ over incidents. The diagonal equals each domain's prevalence count; off-diagonal cells show which domains fail together (e.g., D1 with D4).")
pv.table([""] + [f"D{bb}" for bb in range(1, 9)], rows, fmts=[None] + ["0"] * 8)

# =============================================================== 08 RQ2 chi-square
r2 = Calc("08_RQ2_ChiSquare", "RQ2 – Is the domain family related to whether exploitation needs user interaction?",
          "H₀2: domain family (A Agency & oversight, B Input & code integrity, C Data protection, D Transparency & accountability) is independent of CVSS user interaction (UI:N vs UI:R). "
          "Family comes from each incident's primary domain; 2 incidents with no UI value are excluded (n = 221).", "Section 4 Results – RQ2 (cross-tab, chi-square, Cramér's V)")
crosstab(r2, "r2", ["A", "B", "C", "D"], DR("family"), [0, 1], DR("ui_required"), ["No interaction (UI:N)", "Interaction required (UI:R)"],
         rowlabels=["A Agency and oversight", "B Input and code integrity", "C Data protection", "D Transparency and accountability"],
         report={"chi": round(S["rq2"]["chi2"], 3), "df": 3, "p": S["rq2"]["p"], "N": 221, "V": S["rq2"]["V"], "minE": S["rq2"]["min_expected"], "nlt5": 2,
                 "pex": "p ≈ .70 – far above .05. We do not reject H₀2: the need for user interaction is spread similarly across the families."})
r2.section("Robustness checks for small expected counts")
r2.row(None, "Monte Carlo permutation p-value (10,000 shuffles)", S["rq2"]["mc_p"], "share of shuffled χ² ≥ observed",
       "Typed from Python. We shuffled the UI labels 10,000 times and recomputed χ² each time; 83% of shuffles gave a χ² at least as large – confirming 'no association' without relying on large-sample theory.",
       round(S["rq2"]["mc_p"], 3), 0.001, "0.000", kind="input")
mA = f'(COUNTIFS({DR("family")},"A",{DR("ui_required")},{{v}})+COUNTIFS({DR("family")},"D",{DR("ui_required")},{{v}}))'
r2.note("Merged check: family D has only 1 case, so it is merged into A and the test re-run on a 3×2 table.")
rows = [["A+D merged", "=" + mA.replace("{v}", "0"), "=" + mA.replace("{v}", "1")],
        ["B", f'=COUNTIFS({DR("family")},"B",{DR("ui_required")},0)', f'=COUNTIFS({DR("family")},"B",{DR("ui_required")},1)'],
        ["C", f'=COUNTIFS({DR("family")},"C",{DR("ui_required")},0)', f'=COUNTIFS({DR("family")},"C",{DR("ui_required")},1)']]
fm, lm = r2.table(["Family", "UI:N", "UI:R"], rows, fmts=[None, "0", "0"])
chi_terms = "+".join(f"(({cc_}{rr}-SUM($C{rr}:$D{rr})*SUM({cc_}${fm}:{cc_}${lm})/SUM($C${fm}:$D${lm}))^2/(SUM($C{rr}:$D{rr})*SUM({cc_}${fm}:{cc_}${lm})/SUM($C${fm}:$D${lm})))"
                     for rr in range(fm, lm + 1) for cc_ in "CD")
r2.row("r2m.chi", "Merged χ² (df = 2)", "=" + chi_terms, "Σ (O−E)²/E on the 3×2 table", "", round(S["rq2"]["merged_chi2"], 3), 0.002, "0.000")
r2.row(None, "Merged p-value", "=CHIDIST({r2m.chi},2)", "", "Still far from significant (p ≈ .71). Conclusion unchanged.", round(S["rq2"]["merged_p"], 3), 0.002, "0.000")
r2.row(None, "Achieved power at n = 221, w = .25", round(S["rq2"]["power_w25"], 3), "1 − F_ncχ²(crit; 3, 221·w²)",
       "Typed from Python (exact non-central χ²; tab 05 shows an Excel approximation). 89% power means a true small-to-medium association would very likely have been detected – so the null result is informative.",
       round(S["rq2"]["power_w25"], 3), 0.001, "0.000", kind="input")

# =============================================================== 12 Classification metrics
cm = Calc("12_Model_Metrics", "Model evaluation – confusion matrix, accuracy, F1, balanced accuracy, Brier score and AUC",
          "Applied to the 56 hold-out test cases for the best model (M7 random forest: ACEG profile + CWE) and the GCS logistic model (M2). Change the blue threshold to see the trade-off.",
          "Section 4 Results – Predictive modelling (model comparison table, confusion matrix, ROC)")
cm.row("cm.thr", "Classification threshold", 0.5, "predict 1 if p̂ > t", "Default 0.5, as used by scikit-learn's predict(). Lower it to catch more high-impact cases at the cost of more false alarms.", None, None, "0.00", kind="input")
for r in range(T1, TN + 1):
    wt[f"E{r}"] = f"=IF(C{r}>{ref('cm.thr', 'TestSet')},1,0)"
    wt[f"F{r}"] = f"=IF(D{r}>{ref('cm.thr', 'TestSet')},1,0)"
    wt[f"G{r}"] = f"=SUMPRODUCT(--($C${T1}:$C${TN}<C{r}))+(SUMPRODUCT(--($C${T1}:$C${TN}=C{r}))+1)/2"
    wt[f"H{r}"] = f"=SUMPRODUCT(--($D${T1}:$D${TN}<D{r}))+(SUMPRODUCT(--($D${T1}:$D${TN}=D{r}))+1)/2"
    for cc_ in "EFGH":
        wt[f"{cc_}{r}"].font = F_CALC
TY = f"TestSet!$B${T1}:$B${TN}"
perf = T("model_performance").set_index("key")
for mk, pc, prc, rkc in [("M7", "D", "F", "H"), ("M2", "C", "E", "G")]:
    P_ = f"TestSet!${pc}${T1}:${pc}${TN}"; PR = f"TestSet!${prc}${T1}:${prc}${TN}"; RK = f"TestSet!${rkc}${T1}:${rkc}${TN}"
    pr = perf.loc[mk]
    cm.section(f"{mk} – {pr.Model}")
    k = mk.lower()
    cm.row(f"{k}.tp", "True positives (TP)", f"=COUNTIFS({TY},1,{PR},1)", "y=1, ŷ=1", "High-impact incidents correctly flagged.", None, None, "0")
    cm.row(f"{k}.fn", "False negatives (FN)", f"=COUNTIFS({TY},1,{PR},0)", "y=1, ŷ=0", "High-impact incidents the model missed – the costly error in security triage.", None, None, "0")
    cm.row(f"{k}.fp", "False positives (FP)", f"=COUNTIFS({TY},0,{PR},1)", "y=0, ŷ=1", "Lower-impact incidents wrongly flagged as high.", None, None, "0")
    cm.row(f"{k}.tn", "True negatives (TN)", f"=COUNTIFS({TY},0,{PR},0)", "y=0, ŷ=0", "Lower-impact incidents correctly left alone.", None, None, "0")
    cm.row(None, "Accuracy", f"=({{{k}.tp}}+{{{k}.tn}})/COUNT({TY})", "(TP+TN)/n", "Share of all test cases classified correctly.", pr.test_acc, 0.001, "0.000")
    cm.row(f"{k}.prec", "Precision", f"={{{k}.tp}}/({{{k}.tp}}+{{{k}.fp}})", "TP/(TP+FP)", "When the model says 'high impact', how often is it right?", pr.test_prec, 0.001, "0.000")
    cm.row(f"{k}.rec", "Recall (sensitivity)", f"={{{k}.tp}}/({{{k}.tp}}+{{{k}.fn}})", "TP/(TP+FN)", "Of all truly high-impact incidents, how many did it catch?", pr.test_rec, 0.001, "0.000")
    cm.row(f"{k}.spec", "Specificity", f"={{{k}.tn}}/({{{k}.tn}}+{{{k}.fp}})", "TN/(TN+FP)", "Of all lower-impact incidents, how many did it correctly leave alone? (M2 almost never does – it predicts 'high' for nearly everyone.)", pr.test_spec, 0.001, "0.000")
    cm.row(None, "F1 score", f"=2*{{{k}.prec}}*{{{k}.rec}}/({{{k}.prec}}+{{{k}.rec}})", "2PR/(P+R)", "Harmonic mean of precision and recall.", pr.test_f1, 0.001, "0.000")
    cm.row(None, "Balanced accuracy", f"=({{{k}.rec}}+{{{k}.spec}})/2", "(sensitivity + specificity)/2",
           "Fairer than accuracy when 70% of cases are one class: a model that always says 'high' gets 0.70 accuracy but only 0.50 balanced accuracy.", pr.test_bal_acc, 0.001, "0.000", key_row=True)
    cm.row(None, "Brier score", f"=SUMPRODUCT(({P_}-{TY})^2)/COUNT({TY})", "Σ(p̂ − y)²/n", "Mean squared error of the probabilities (0 = perfect; 0.21 = always predicting 70%). Lower is better.", pr.test_brier, 0.001, "0.000")
    cm.row(f"{k}.n1", "Positives in test set n₁", f"=SUM({TY})", "", "", 39, 0, "0")
    cm.row(f"{k}.n0", "Negatives in test set n₀", f"=COUNT({TY})-SUM({TY})", "", "", 17, 0, "0")
    cm.row(None, "AUC (area under ROC curve)", f"=(SUMIF({TY},1,{RK})-{{{k}.n1}}*({{{k}.n1}}+1)/2)/({{{k}.n1}}*{{{k}.n0}})",
           "AUC = [Σ ranks of positives − n₁(n₁+1)/2] / (n₁n₀)",
           "Rank all 56 predicted probabilities. AUC is the chance that a random high-impact case gets a higher score than a random lower-impact case – the same maths as Mann–Whitney U (tab 11). 0.5 = coin flip, 1 = perfect. Independent of the threshold.",
           pr.test_auc, 0.001, "0.000", key_row=True)

# =============================================================== 13 Model comparison
mc = Calc("13_Model_Comparison", "Model comparison – train/test split, cross-validated AUC, overfitting gap and best-model selection",
          "Eight models (M0 baseline to M7) were trained in Python on the same 167-case training split and tested on the same 56 cases. Their scores are typed in (blue); Excel does the comparisons.",
          "Section 3 Methodology – Modelling plan; Section 4 Results – Model comparison table")
mc.section("Stratified 75/25 split arithmetic")
mc.row("mc.N", "All incidents", 223, "N", "", None, None, "0", kind="input")
mc.row("mc.nt", "Test-set size", "=ROUNDUP({mc.N}*0.25,0)", "⌈0.25·N⌉", "scikit-learn rounds the test share up: 55.75 → 56.", S["split"]["test"], 0, "0")
mc.row(None, "Training-set size", "={mc.N}-{mc.nt}", "N − test", "", S["split"]["train"], 0, "0")
mc.row(None, "High-impact cases in test set (stratified)", "=ROUND({mc.nt}*156/{mc.N},0)", "round(56 × 156/223)",
       "Stratification keeps the 70/30 class balance identical in both parts: 39 of 56 test cases are high impact.", S["split"]["test_hi"], 0, "0")
mc.section("Performance table (inputs from Python) with Excel-derived comparisons")
rows = []
for kk in perf.index:
    pr = perf.loc[kk]
    rows.append([pr.Model, pr.train_auc, pr.cv_auc, pr.cv_auc_sd, pr.test_auc, pr.test_bal_acc, pr.test_brier,
                 "=C{rr}-F{rr}", "=F{rr}-0.5", "=RANK(D{rr},$D${f}:$D${l})"])
mc.note("Overfitting gap = training AUC − test AUC (big gap = memorising). Gain over chance = test AUC − 0.5. Rank uses the 5×10 cross-validated AUC – the criterion fixed in advance for choosing the best model.")
f0 = mc.r + 1
rows = [[x.replace("{f}", str(f0)).replace("{l}", str(f0 + 7)) if isinstance(x, str) else x for x in rw] for rw in rows]
f, l_ = mc.table(["Model", "Train AUC", "CV AUC (mean)", "CV AUC SD", "Test AUC", "Test balanced acc.", "Test Brier", "Overfit gap", "Gain over chance", "Rank by CV AUC"],
                 rows, fmts=[None, "0.000", "0.000", "0.000", "0.000", "0.000", "0.000", "0.000", "0.000", "0"],
                 kinds=["text", "input", "input", "input", "input", "input", "input", "calc", "calc", "calc"])
mc.row(None, "Best model by CV AUC", f"=INDEX(B{f}:B{l_},MATCH(MAX(D{f}:D{l_}),D{f}:D{l_},0))", "argmax CV AUC", "M7 (random forest on the ACEG profile plus CWE groups) is selected.", None, None, "@", key_row=True)
mc.row(None, "Test AUC gain of M7 over the GCS logistic model M2", f"=F{l_}-F{f + 2}", "AUC_M7 − AUC_M2",
       "The full ACEG control profile adds about 0.14 AUC over the single GCS number.", round(S["auc_diff"]["M2"]["mean"], 3), 0.01, "0.000")
mc.row(None, "Bootstrap 95% CI for that gain – low", round(S["auc_diff"]["M2"]["lo"], 3), "2.5th percentile of 2,000 resamples",
       "Typed from Python (paired bootstrap of the 56 test cases). The CI just touches 0, and 97.5% of resamples favoured M7 (one-sided p ≈ .026).", round(S["auc_diff"]["M2"]["lo"], 3), 0.001, "0.000", kind="input")
mc.row(None, "Bootstrap 95% CI for that gain – high", round(S["auc_diff"]["M2"]["hi"], 3), "97.5th percentile", "", round(S["auc_diff"]["M2"]["hi"], 3), 0.001, "0.000", kind="input")
mc.row(None, "Test AUC gain of M7 over CWE-based triage M3", f"=F{l_}-F{f + 3}", "AUC_M7 − AUC_M3", "ACEG adds about 0.14 AUC over today's CWE-based triage too.", round(S["auc_diff"]["M3"]["mean"], 3), 0.01, "0.000")

# =============================================================== 14 CV & importance
ci = Calc("14_CV_and_Importance", "Repeated cross-validation and permutation feature importance",
          "How the 'CV AUC' numbers on tab 13 are produced, and which ACEG features the best model relies on.", "Section 3 Methodology – Validation; Section 4 Results – Feature importance")
ci.row("ci.k", "Folds per repetition (k)", 5, "k", "The 167 training cases are cut into 5 equal parts; each part takes a turn as the mini-test set.", None, None, "0", kind="input")
ci.row("ci.r", "Repetitions", 10, "r", "The 5-fold cut is reshuffled 10 times so the result does not depend on one lucky split.", None, None, "0", kind="input")
ci.row("ci.fits", "Models fitted per algorithm", "={ci.k}*{ci.r}", "k × r", "50 AUC values per model; tab 13 reports their mean and SD.", 50, 0, "0")
ci.row(None, "Approximate cases per validation fold", "=167/{ci.k}", "n_train / k", "About 33 cases are held back each time; the other ~134 train the model.", None, None, "0.0")
ci.row(None, "M7 CV AUC – mean (input)", perf.loc["M7"].cv_auc, "mean of 50 AUCs", "", None, None, "0.000", kind="input")
ci.row(None, "Rough standard error of that mean", f"={perf.loc['M7'].cv_auc_sd}/SQRT({{ci.fits}})", "SD / √50",
       "Indicative only – folds overlap so the 50 AUCs are not independent; the true uncertainty is larger. This is why the report also gives bootstrap CIs on the hold-out test set.", None, None, "0.000")
ci.section("Permutation importance (M7, test set; 30 shuffles per feature)")
ci.note("Recipe: shuffle one feature's column so it carries no information, re-score the model, and record how much the AUC drops. Repeat 30 times; mean drop = importance. Bigger drop = the model leans on that feature more. Values typed from Python.")
im = T("model_permutation_importance").head(12)
rows = [[r_.feature, r_["mean"], r_["sd"], "=C{rr}/SUM($C$" + "{f}" + ":$C$" + "{l}" + ")", "=RANK(C{rr},$C${f}:$C${l})", "=IF(C{rr}-2*D{rr}>0,\"clearly > 0\",\"within noise\")"] for _, r_ in im.iterrows()]
f0 = ci.r + 1
rows = [[x.replace("{f}", str(f0)).replace("{l}", str(f0 + len(im) - 1)) if isinstance(x, str) else x for x in rw] for rw in rows]
ci.table(["Feature", "Mean AUC drop", "SD", "Share of top-12 importance", "Rank", "Mean − 2·SD > 0?"], rows,
         fmts=[None, "0.0000", "0.0000", "0.0%", "0", None], kinds=["input", "input", "input", "calc", "calc", "calc"])
ci.note("d1 = Agency and action control present; n_domains = number of domains; bNN = control NN breached. The top features are ACEG domains and controls, which is the evidence that the framework itself carries predictive signal.")

# =============================================================== 15 RQ4 pairwise kappa
kp = Calc("15_RQ4_Kappa_Pairwise", "RQ4 – Inter-rater agreement: Cohen's kappa for each pair of coders, per domain",
          "κ = (pₒ − pₑ)/(1 − pₑ): observed agreement pₒ corrected for the agreement pₑ expected by chance from each coder's base rates. "
          "κ < .20 slight, .21–.40 fair, .41–.60 moderate, .61–.80 substantial (Landis & Koch, 1977).", "Section 4 Results – RQ4 (agreement table)")
pk_ = T("rq4_pairwise_kappa").set_index("Item")
for pa_, pb_, lab, colk in [("C1", "C2", "Coder 1 vs Coder 2 (human–human)", "k_C1_C2"), ("C1", "LLM", "Coder 1 vs LLM", "k_C1_LLM"), ("C2", "LLM", "Coder 2 vs LLM", "k_C2_LLM")]:
    kp.section(lab)
    rows = []
    for j in range(1, 9):
        A_, B_ = CR(f"{pa_}_d{j}"), CR(f"{pb_}_d{j}")
        rows.append([f"D{j}", f"=SUMPRODUCT({A_},{B_})", f"=SUMPRODUCT((1-{A_})*(1-{B_}))", f"=(C{{rr}}+D{{rr}})/{N}",
                     f"=AVERAGE({A_})", f"=AVERAGE({B_})", "=F{rr}*G{rr}+(1-F{rr})*(1-G{rr})",
                     '=IF(H{rr}=1,"n/a",(E{rr}-H{rr})/(1-H{rr}))', float(pk_.loc[f"D{j}", colk]),
                     '=IF(I{rr}="n/a","",IF(ABS(I{rr}-J{rr})<0.0015,"✓","check"))'])
    rows = [[x.replace("{{rr}}", "{rr}") if isinstance(x, str) else x for x in rw] for rw in rows]
    kp.table(["Domain", "Both say 1", "Both say 0", "pₒ = agree / 223", f"Rate {pa_}", f"Rate {pb_}", "pₑ = r₁r₂ + (1−r₁)(1−r₂)", "κ", "Report κ", "Check"], rows,
             fmts=[None, "0", "0", "0.000", "0.000", "0.000", "0.000", "0.000", "0.000", None],
             kinds=["text", "calc", "calc", "calc", "calc", "calc", "calc", "calc", "input", "calc"])
kp.note("Read-across: D3 and D7 have κ ≈ 0 because Coder 2 never used them while Coder 1 used them often – a codebook-interpretation gap, not random noise. D4 and D5 reach moderate agreement.")
kp.section("Pooled human–human kappa (all 223 × 8 = 1,784 domain cells together)")
A_all = f"Coders!${CC['C1_d1']}${R1}:${CC['C1_d8']}${RN}"; B_all = f"Coders!${CC['C2_d1']}${R1}:${CC['C2_d8']}${RN}"
kp.row("kp.n", "Cells", f"=COUNT({A_all})", "223 × 8", "", 1784, 0, "0")
kp.row("kp.po", "Observed agreement pₒ", f"=SUMPRODUCT(--({A_all}={B_all}))/{{kp.n}}", "Σ[a=b]/cells", "", None, None, "0.000")
kp.row("kp.ra", "Coder 1 rate of 1s", f"=SUM({A_all})/{{kp.n}}", "", "", None, None, "0.000")
kp.row("kp.rb", "Coder 2 rate of 1s", f"=SUM({B_all})/{{kp.n}}", "", "", None, None, "0.000")
kp.row("kp.pe", "Chance agreement pₑ", "={kp.ra}*{kp.rb}+(1-{kp.ra})*(1-{kp.rb})", "", "", None, None, "0.000")
kp.row(None, "Pooled human–human κ", "=({kp.po}-{kp.pe})/(1-{kp.pe})", "κ = (pₒ − pₑ)/(1 − pₑ)",
       "Only 'fair' (.28). The two humans disagree quite often – which matters for RQ4: the LLM is judged only on the cells where the humans agree (tab 16).", round(S["rq4"]["hh_pooled_kappa"], 3), 0.001, "0.000", key_row=True)
kp.row(None, "Bootstrap 95% CI (low – high)", f'="{S["rq4"]["hh_lo"]:.3f} – {S["rq4"]["hh_hi"]:.3f}"', "2,000 case resamples",
       "Typed from Python: resample the 223 incidents with replacement 2,000 times and recompute κ.", None, None, "@", kind="input")
kp.section("Primary-domain agreement (8 categories) – Coder 1 vs Coder 2")
rows = [[f"D{j}", f'=COUNTIF({CR("C1_primary")},{j})/{N}', f'=COUNTIF({CR("C2_primary")},{j})/{N}', "=C{rr}*D{rr}"] for j in range(1, 9)]
fp_, lp_ = kp.table(["Primary domain", "Share C1", "Share C2", "Product"], rows, fmts=[None, "0.000", "0.000", "0.0000"])
kp.row("kp.ppo", "pₒ – same primary domain", f"=SUMPRODUCT(--({CR('C1_primary')}={CR('C2_primary')}))/{N}", "Σ[a=b]/n", "", round(S["rq4"]["primary"]["po_C1_C2"], 3), 0.001, "0.000")
kp.row("kp.ppe", "pₑ = Σ shares product", f"=SUM(E{fp_}:E{lp_})", "Σₖ p₁ₖp₂ₖ", "With 8 categories, chance agreement is the sum over categories.", None, None, "0.000")
kp.row(None, "Multi-class κ (primary domain)", "=({kp.ppo}-{kp.ppe})/(1-{kp.ppe})", "κ = (pₒ − pₑ)/(1 − pₑ)", "Fair (.22): choosing the single 'main' domain is harder than flagging all present domains.", round(S["rq4"]["primary"]["k_C1_C2"], 3), 0.001, "0.000")

# =============================================================== 16 RQ4 LLM vs consensus
lv = Calc("16_RQ4_LLM_vs_Consensus", "RQ4 – Can an LLM coder replace human coding? LLM vs human consensus",
          "H₀4: LLM agreement with human consensus κ ≤ .60. Reference = cells where Coder 1 and Coder 2 agree (their shared answer is treated as truth). "
          "For each domain we build a 2×2 table of consensus vs LLM.", "Section 4 Results – RQ4 (LLM vs consensus table, pooled kappa)")
lc = T("rq4_llm_vs_consensus").set_index("Item")
rows = []
for j in range(1, 9):
    A_, B_, Lm = CR(f"C1_d{j}"), CR(f"C2_d{j}"), CR(f"LLM_d{j}")
    m = f"--({A_}={B_})"
    rows.append([f"D{j}", f"=SUMPRODUCT({m})", f"=SUMPRODUCT({m},{A_},{Lm})", f"=SUMPRODUCT({m},1-{A_},{Lm})",
                 f"=SUMPRODUCT({m},{A_},1-{Lm})", "=C{rr}-D{rr}-E{rr}-F{rr}", "=(D{rr}+G{rr})/C{rr}",
                 '=IFERROR(D{rr}/(D{rr}+E{rr}),"n/a")', '=IFERROR(D{rr}/(D{rr}+F{rr}),"n/a")',
                 "=((D{rr}+F{rr})*(D{rr}+E{rr})+(G{rr}+E{rr})*(G{rr}+F{rr}))/C{rr}^2",
                 '=IFERROR((H{rr}-K{rr})/(1-K{rr}),"n/a")', float(lc.loc[f"D{j}", "kappa"]) if not pd.isna(lc.loc[f"D{j}", "kappa"]) else "n/a"])
rows = [[x.replace("{{rr}}", "{rr}") if isinstance(x, str) else x for x in rw] for rw in rows]
f, l_ = lv.table(["Domain", "Consensus cases", "TP (both 1)", "FP (LLM 1, humans 0)", "FN (LLM 0, humans 1)", "TN", "Accuracy", "Precision", "Recall",
                  "pₑ", "κ", "Report κ"], rows,
                 fmts=[None, "0", "0", "0", "0", "0", "0.000", "0.000", "0.000", "0.000", "0.000", "0.000"],
                 kinds=["text"] + ["calc"] * 10 + ["input"])
lv.note("pₑ = [(TP+FN)(TP+FP) + (TN+FP)(TN+FN)] / n² – the chance that consensus and LLM agree given their base rates. D3 and D7 have no consensus positives, so κ is undefined (n/a).")
lv.section("Pooled across all domain cells where the humans agree (the headline RQ4 test)")
for nm, col in [("n", "C"), ("tp", "D"), ("fp", "E"), ("fn", "F"), ("tn", "G")]:
    lv.row(f"lv.{nm}", {"n": "Consensus cells", "tp": "TP", "fp": "FP", "fn": "FN", "tn": "TN"}[nm], f"=SUM({col}{f}:{col}{l_})", "Σ over 8 domains",
           "", {"n": S["rq4"]["pooled_cells"], "fp": S["rq4"]["pooled_fp"], "fn": S["rq4"]["pooled_fn"]}.get(nm), 0, "0")
lv.row("lv.acc", "Accuracy", "=({lv.tp}+{lv.tn})/{lv.n}", "(TP+TN)/n", "", S["rq4"]["pooled_acc"], 0.001, "0.000")
lv.row("lv.prec", "Precision", "={lv.tp}/({lv.tp}+{lv.fp})", "TP/(TP+FP)", "The LLM over-flags: about 1 in 3 of its positives are not confirmed by the humans.", S["rq4"]["pooled_prec"], 0.001, "0.000")
lv.row("lv.rec", "Recall", "={lv.tp}/({lv.tp}+{lv.fn})", "TP/(TP+FN)", "It catches about 77% of the domains the humans agree are present.", S["rq4"]["pooled_rec"], 0.001, "0.000")
lv.row(None, "F1", "=2*{lv.prec}*{lv.rec}/({lv.prec}+{lv.rec})", "2PR/(P+R)", "", S["rq4"]["pooled_f1"], 0.001, "0.000")
lv.row("lv.pe", "Chance agreement pₑ", "=(({lv.tp}+{lv.fn})*({lv.tp}+{lv.fp})+({lv.tn}+{lv.fp})*({lv.tn}+{lv.fn}))/{lv.n}^2", "", "", None, None, "0.000")
lv.row("lv.k", "Pooled κ (LLM vs consensus)", "=({lv.acc}-{lv.pe})/(1-{lv.pe})", "κ = (pₒ − pₑ)/(1 − pₑ)",
       "Moderate (.58) – twice the human–human κ (.28), but below the .60 'substantial' bar set in H₀4.", round(S["rq4"]["pooled_kappa"], 3), 0.001, "0.000", key_row=True)
lv.row(None, "Bootstrap 95% CI", f'="{S["rq4"]["pooled_lo"]:.3f} – {S["rq4"]["pooled_hi"]:.3f}"', "2,000 case resamples", "Typed from Python. The CI includes .60.", None, None, "@", kind="input")
lv.row(None, "Share of bootstrap κ ≤ .60 (one-sided p for H₀4)", S["rq4"]["p_le_60"], "P(κ* ≤ .60)",
       "Typed from Python. 80% of resamples fall at or below .60, so we cannot reject H₀4: the LLM is a useful assistant (it agrees with consensus far better than the humans agree with each other) but not yet a replacement for human review.",
       S["rq4"]["p_le_60"], 0.001, "0.000", kind="input")

# =============================================================== 17 Fleiss
fl = Calc("17_RQ4_Fleiss", "RQ4 – Fleiss' kappa: agreement among all three coders at once",
          "For each incident count how many of the 3 coders said 'present' (s = 0–3). Agreement within the case Pᵢ = [s² + (3−s)² − 3] / (3·2). Fleiss κ = (P̄ − Pₑ)/(1 − Pₑ).",
          "Section 4 Results – RQ4 (agreement table, Fleiss column)")
rows = []
for j in range(1, 9):
    s = f"({CR(f'C1_d{j}')}+{CR(f'C2_d{j}')}+{CR(f'LLM_d{j}')})"
    rows.append([f"D{j}", f"=SUMPRODUCT(({s}^2+(3-{s})^2-3)/6)/{N}", f"=SUMPRODUCT({s})/(3*{N})", "=D{rr}^2+(1-D{rr})^2",
                 '=IF(E{rr}=1,"n/a",(C{rr}-E{rr})/(1-E{rr}))', float(pk_.loc[f"D{j}", "fleiss"])])
rows = [[x.replace("{{rr}}", "{rr}") if isinstance(x, str) else x for x in rw] for rw in rows]
f, l_ = fl.table(["Domain", "P̄ (mean within-case agreement)", "p = share of 'present' votes", "Pₑ = p² + (1−p)²", "Fleiss κ", "Report"], rows,
                 fmts=[None, "0.000", "0.000", "0.000", "0.000", "0.000"], kinds=["text", "calc", "calc", "calc", "calc", "input"])
fl.row("fl.P", "Pooled P̄ (all 1,784 cells)", f"=AVERAGE(C{f}:C{l_})", "mean of domain P̄ (equal n per domain)", "", None, None, "0.000")
fl.row("fl.p", "Pooled p", f"=AVERAGE(D{f}:D{l_})", "", "", None, None, "0.000")
fl.row("fl.pe", "Pooled Pₑ", "={fl.p}^2+(1-{fl.p})^2", "", "", None, None, "0.000")
fl.row(None, "Pooled Fleiss κ", "=({fl.P}-{fl.pe})/(1-{fl.pe})", "κ = (P̄ − Pₑ)/(1 − Pₑ)", "Fair overall agreement (.34) across the three coders.", round(S["rq4"]["fleiss_pooled"], 3), 0.001, "0.000", key_row=True)

# =============================================================== 18 Majority vote
mv = Calc("18_Majority_Vote", "Final (gold) labels – 2-of-3 majority vote",
          "Each domain is marked present in the final dataset when at least 2 of the 3 coders (Coder 1, Coder 2, LLM) marked it; if no domain reaches 2 votes, the most-voted domain is kept (fallback). The Coders tab recomputes this for every incident (green 'Maj_' columns).",
          "Section 3 Methodology – Coding procedure and final labels")
for j in range(1, 9):
    mv.row(None, f"D{j}: incidents where majority = stored gold label", f"=SUMPRODUCT(--({CR(f'Maj_d{j}')}={CR(f'Gold_d{j}')}))", "Σ[majority = gold]",
           "Must be 223 for every domain – proves the final labels were built exactly by the 2-of-3 rule." if j == 1 else "", 223, 0, "0")
mv.row(None, "Incidents with no domain reaching 2 votes (fallback rule used)", f'=COUNTIF({CR("Top votes")},"<2")', "count(top votes < 2)",
       "For these incidents the three coders each picked different domains. Rather than leave the incident with no domain, the rule keeps the domain with the most votes; a tie is broken by the causal order D4, D6, D2, D1, D8, D5, D3, D7 (Coders!Fallback domain).", None, None, "0")
mv.row(None, "Incidents where all 8 domains match", f"=SUM({CR('Maj=Gold all 8')})", "", "", 223, 0, "0", key_row=True)
mv.row(None, "Incidents where all three coders agree on all 8 domains", f"=SUM({CR('Unanimous all 8')})", "",
       "Only 3 – full unanimity is rare, which is why a majority rule (rather than requiring agreement) was needed.", S["rq4"]["unanimous_cases"], 0, "0")
mv.note("Primary domain: when the three coders name three different primary domains, the tie is broken by the fixed priority order D4, D6, D2, D1, D8, D5, D3, D7 (most to least specific), decided before analysis.")

# =============================================================== 19 Skill tiers
sk = Calc("19_Skill_Validation", "Industry skill – does the priority tier track real impact?",
          "The ACEG governance skill assigns each test incident a priority tier (P1 fix before agent use, P2 this sprint, P3 routine). A good triage tool should show a falling share of high-impact incidents from P1 to P3.",
          "Section 5 – Industry solution (skill evaluation table)")
st = T("skill_tier_validation")
rows = [[r_.tier, int(r_["count"]), int(r_["sum"]), "=D{rr}/C{rr}",
         f"=(E{{rr}}+{z}^2/(2*C{{rr}})-{z}*SQRT(E{{rr}}*(1-E{{rr}})/C{{rr}}+{z}^2/(4*C{{rr}}^2)))/(1+{z}^2/C{{rr}})".replace("{{rr}}", "{rr}"),
         f"=(E{{rr}}+{z}^2/(2*C{{rr}})+{z}*SQRT(E{{rr}}*(1-E{{rr}})/C{{rr}}+{z}^2/(4*C{{rr}}^2)))/(1+{z}^2/C{{rr}})".replace("{{rr}}", "{rr}"),
         float(r_["mean"])] for _, r_ in st.iterrows()]
f, l_ = sk.table(["Tier", "Incidents in tier", "Of which high impact", "Share high impact", "Wilson low", "Wilson high", "Report share"], rows,
                 fmts=[None, "0", "0", "0.0%", "0.0%", "0.0%", "0.0%"], kinds=["text", "input", "input", "calc", "calc", "calc", "input"])
sk.row(None, "Tiers fall monotonically (P1 > P2 > P3)?", f'=IF(AND(E{f}>E{f + 1},E{f + 1}>E{f + 2}),"Yes","No")', "",
       "90% → 74% → 31%: the tiers order incidents by real-world severity.", None, None, "@", key_row=True)
sk.row(None, "Difference P1 − P3", f"=E{f}-E{f + 2}", "", "Almost 60 percentage points between the top and bottom tier.", None, None, "0.0%")
ev = T("skill_evaluation")
sk.row(None, "Fully automated (LLM-only labels) test AUC", float(ev.test_auc[1]), "input",
       "Typed from Python. Running the skill end-to-end with only the LLM coder still gives AUC .81 – close to .84 with human-checked labels.", float(ev.test_auc[1]), 0.001, "0.000", kind="input")

# =============================================================== README
rd = wb.create_sheet("00_README", 0)
rd.column_dimensions["A"].width = 26; rd.column_dimensions["B"].width = 70; rd.column_dimensions["C"].width = 52
rd["A1"] = "Group 3 – QM640 Capstone: ACEG Framework – Statistical calculations workbook"; rd["A1"].font = F_T
rd["A2"] = ("Every number the final report computes, rebuilt with live Excel formulas from the coded data, with a plain-language explanation beside each step. "
            "Use it to learn the methods and to walk the mentor through how each result was obtained.")
rd["A2"].alignment = WRAP; rd["A2"].font = F_ST; rd.merge_cells("A2:C2"); rd.row_dimensions[2].height = 36
rd["A4"] = "How each calculation tab reads (left → right)"; rd["A4"].font = F_SEC
lay = [("Step", "Order of the calculation."), ("What we calculate", "Name of the quantity in everyday words."),
       ("Value", "The live Excel result (yellow fill = a headline result quoted in the report)."), ("The maths", "The formula in statistical notation."),
       ("Excel formula", "The exact formula in the Value cell, shown as text so you can read it without clicking."),
       ("Plain-language explanation", "What the step means and why it matters – written for a learner and for presenting to the mentor."),
       ("Value in the report", "The figure printed in the final report (blue)."), ("Check", "✓ matches when Excel reproduces the report value within rounding.")]
r = 5
for a, b_ in lay:
    rd.cell(r, 1, a).font = Font(name=AR, size=10, bold=True); rd.cell(r, 2, b_).font = F_TXT; r += 1
r += 1
rd.cell(r, 1, "Colour code").font = F_SEC; r += 1
for txt, fnt, fl_ in [("Blue text", F_IN, None), ("Black text", F_CALC, None), ("Green text", F_LINK, None), ("Yellow fill", F_CALC, FILL_KEY)]:
    cl = rd.cell(r, 1, txt); cl.font = fnt
    if fl_: cl.fill = fl_
    rd.cell(r, 2, {"Blue text": "Typed input: coded data, a model output that Excel cannot compute, or a value from the report.",
                   "Black text": "Excel formula calculated on this sheet.",
                   "Green text": "Formula that pulls a value from another sheet.",
                   "Yellow fill": "Headline result that appears in the report."}[txt]).font = F_TXT
    r += 1
r += 1
rd.cell(r, 1, "Tab index").font = F_SEC; r += 1
for j, h in enumerate(["Tab", "What it calculates", "Report section"], 1):
    cl = rd.cell(r, j, h); cl.font = F_H; cl.fill = FILL_H
r += 1
idx = [("Data", "223 incidents with final labels, controls, CVSS, and per-case formula columns (GCS, z-score, logistic prediction, ranks)", "Data source for all tabs"),
       ("Coders", "Domain labels from Coder 1, Coder 2, LLM and the final (gold) labels; majority-vote formulas", "RQ4, coding procedure"),
       ("TestSet", "56 hold-out cases with model probabilities; predicted class and ranks", "Model evaluation"),
       ("01_GCS_WorkedExample", "Governance Compliance Score for any incident, control by control", "Methodology – Measures"),
       ("02_CVSS_Recovery", "CVSS 3.1 base score rebuilt from its vector (data cleaning)", "Methodology – Data cleaning"),
       ("03_EDA_Descriptives", "Mean, median, SD, quartiles, IQR, Tukey outliers, skewness, counts", "Results – EDA"),
       ("04_EDA_ChiSquare", "Chi-square and Cramér's V: CWE group × high impact; ecosystem × high impact", "Results – EDA"),
       ("05_SampleSize", "Required sample size for RQ1–RQ4 and achieved power", "Methodology – Sample size"),
       ("06_RQ1_Coverage", "Coverage, Wilson 95% CI, exact binomial test vs 80%", "Results – RQ1"),
       ("07_RQ1_Prevalence", "Domain prevalence with CIs, control breach rates, co-occurrence matrix", "Results – RQ1"),
       ("08_RQ2_ChiSquare", "Family × user interaction: χ², df, p, Cramér's V, residuals, merged check", "Results – RQ2"),
       ("09_RQ3_Logistic", "Log-likelihood, LR test, McFadden R², SEs via information matrix, z, p, ORs, CIs, VIFs, worked prediction", "Results – RQ3"),
       ("10_RQ3_HosmerLemeshow", "Hosmer–Lemeshow calibration test (10 groups)", "Results – RQ3 diagnostics"),
       ("11_RQ3_MannWhitney", "Mann–Whitney U with tie correction; probability of superiority", "Results – RQ3 robustness"),
       ("12_Model_Metrics", "Confusion matrix, accuracy, precision, recall, specificity, F1, balanced accuracy, Brier, AUC", "Results – Predictive modelling"),
       ("13_Model_Comparison", "Split arithmetic, M0–M7 comparison, overfitting gap, best model, AUC gains", "Results – Model comparison"),
       ("14_CV_and_Importance", "5×10 repeated cross-validation and permutation importance", "Methodology – Validation; Results"),
       ("15_RQ4_Kappa_Pairwise", "Cohen's κ per domain for each coder pair; pooled and primary-domain κ", "Results – RQ4"),
       ("16_RQ4_LLM_vs_Consensus", "LLM vs human consensus: 2×2 tables, precision, recall, pooled κ", "Results – RQ4"),
       ("17_RQ4_Fleiss", "Fleiss' κ for three coders", "Results – RQ4"),
       ("18_Majority_Vote", "Proof that the final labels follow the 2-of-3 majority rule", "Methodology – Coding"),
       ("19_Skill_Validation", "Priority tiers of the industry skill vs real impact", "Industry solution")]
for t_, w_, s_ in idx:
    rd.cell(r, 1, t_).font = Font(name=AR, size=10, bold=True, color="1F3864", underline="single")
    rd.cell(r, 1).hyperlink = f"#'{t_}'!A1"
    rd.cell(r, 2, w_).font = F_TXT; rd.cell(r, 2).alignment = WRAP
    rd.cell(r, 3, s_).font = F_TXT
    r += 1
r += 1
rd.cell(r, 1, "What Excel cannot do (typed in from Python)").font = F_SEC; r += 1
for t_ in ["Logistic-regression coefficients (iterative maximum likelihood). Tab 09 proves they are the maximum: the score equations sum to ~0.",
           "Non-central chi-square λ for the RQ2 power calculation (tab 05 verifies it with the Patnaik approximation).",
           "Random-forest / boosting / neural-network predictions, cross-validation and permutation importance (tabs 12–14 use their outputs).",
           "Bootstrap and Monte Carlo resampling results (confidence intervals for κ and AUC differences, permutation p-value).",
           "Hosmer–Lemeshow: many incidents share the same predicted probability, so the sort order used by Python is typed in (Data!p_rank_py) to reproduce 6.22; tab 10 also shows the Excel row-order version (≈7.6, p ≈ .48) – same conclusion."]:
    rd.cell(r, 1, "•").font = F_TXT; rd.cell(r, 2, t_).font = F_TXT; rd.cell(r, 2).alignment = WRAP
    rd.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3); rd.row_dimensions[r].height = 28
    r += 1
r += 1
rd.cell(r, 1, "Source").font = F_SEC; r += 1
rd.cell(r, 1, "Data and Python outputs from the project repository (data/processed/*.csv, outputs/final/summary.json and tables/*.csv; scripts src/09_final_analysis.py and sample_size/sample_size.py).").font = F_ST

# ---------------------------------------------------------------- order and save
order = ["00_README", "01_GCS_WorkedExample", "02_CVSS_Recovery", "03_EDA_Descriptives", "04_EDA_ChiSquare", "05_SampleSize",
         "06_RQ1_Coverage", "07_RQ1_Prevalence", "08_RQ2_ChiSquare", "09_RQ3_Logistic", "10_RQ3_HosmerLemeshow", "11_RQ3_MannWhitney",
         "12_Model_Metrics", "13_Model_Comparison", "14_CV_and_Importance", "15_RQ4_Kappa_Pairwise", "16_RQ4_LLM_vs_Consensus",
         "17_RQ4_Fleiss", "18_Majority_Vote", "19_Skill_Validation", "Data", "Coders", "TestSet"]
wb._sheets = [wb[n] for n in order]
for wsx in wb.worksheets:
    wsx.sheet_view.showGridLines = wsx.title in ("Data", "Coders", "TestSet")
wb.active = 0
wb.save(OUT)
print("saved", OUT)
