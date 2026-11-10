"""Builds the QM640 final report (docx) from the analysis outputs. Run: python tools/build_report.py"""
import json
import re
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/final"
FIG = OUT / "figures"
T = OUT / "tables"
S = json.load(open(OUT / "summary.json"))
FONT = "Times New Roman"

doc = Document(ROOT / "docs/QM_640_Final_Report_Template.docx")
body = doc.element.body
for el in list(body):
    if el.tag.endswith("sectPr"):
        continue
    body.remove(el)

sec = doc.sections[0]
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Inches(1))
sec.header_distance = Inches(0.5)
sec.different_first_page_header_footer = False

def STY(name):
    for s_ in doc.styles:
        if s_.name == name:
            return s_
    raise KeyError(name)


st = STY("Normal")
st.font.name = FONT
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
pf = st.paragraph_format
pf.line_spacing = 2.0
pf.space_before = Pt(0)
pf.space_after = Pt(0)
for name in ("Heading 1", "Heading 2", "Heading 3", "Title"):
    try:
        hs = STY(name)
    except KeyError:
        continue
    hs.font.name = FONT
    hs.font.size = Pt(12)
    hs.font.color.rgb = RGBColor(0, 0, 0)
    hs.font.bold = True
    hs.font.italic = False
    rpr = hs.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    hs.paragraph_format.space_before = Pt(0)
    hs.paragraph_format.space_after = Pt(0)
    hs.paragraph_format.line_spacing = 2.0
    hs.paragraph_format.keep_with_next = True
    hs.paragraph_format.first_line_indent = Inches(0)
STY("Heading 1").paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
STY("Heading 3").font.italic = True

# page number header (top right)
hdr = sec.header
hp = hdr.paragraphs[0] if hdr.paragraphs else hdr.add_paragraph()
hp.text = ""
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hp.add_run()
for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
    if kind:
        e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), kind); r._r.append(e)
    else:
        e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; r._r.append(e)
r.font.name = FONT
r.font.size = Pt(12)

TOK = re.compile(r"(\*\*.+?\*\*|\*.+?\*|_\{.+?\}|\^\{.+?\})")
# APA 7: statistical symbols in italics (Greek letters and OR/AUC stay roman)
STAT = re.compile(r"(?<![A-Za-z0-9_/.\-])(?:(?:p|n|N|M|r|t)(?=\s?[=<>≤≥])|z(?=\s?[=<>≤≥]|-score)|SDs?(?![A-Za-z])|SEs?(?![A-Za-z])|df(?![A-Za-z])|R²)")
STAT_CELLS = {"p", "SE", "z", "n", "df", "M", "SD", "N", "Mdn"}


def runs(p, text, size=None, bold=False, italic=False):
    text = re.sub(r"(?<=\S) ([=<>≤≥]) (?=\S)", "\u00a0\\1\u00a0", text)
    for part in TOK.split(text):
        if not part:
            continue
        b, i, sub, sup = bold, italic, False, False
        if part.startswith("**"):
            part, b = part[2:-2], True
        elif part.startswith("*"):
            part, i = part[1:-1], True
        elif part.startswith("_{"):
            part, sub = part[2:-1], True
        elif part.startswith("^{"):
            part, sup = part[2:-1], True
        pieces = [(part, False)]
        if not (i or sub or sup):
            if part.strip() in STAT_CELLS:
                pieces = [(part, True)]
            else:
                pieces, last = [], 0
                for m in STAT.finditer(part):
                    pieces.append((part[last:m.start()], False)); pieces.append((m.group(0), True)); last = m.end()
                pieces.append((part[last:], False))
        for txt, it in pieces:
            if not txt:
                continue
            rr = p.add_run(txt)
            rr.bold, rr.italic = b, (i or it)
            rr.font.subscript, rr.font.superscript = sub, sup
            rr.font.name = FONT
            if size:
                rr.font.size = Pt(size)
    return p


def P(text, indent=True, align=None, keep=False, spacing=None):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Inches(0.5) if indent else Inches(0)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if keep:
        p.paragraph_format.keep_with_next = True
    if spacing:
        p.paragraph_format.line_spacing = spacing
    return runs(p, text)


def H1(text, page_break=False):
    if page_break:
        pagebreak()
    p = doc.add_paragraph(style=STY("Heading 1"))
    runs(p, text, bold=True)
    return p


def H2(text):
    p = doc.add_paragraph(style=STY("Heading 2"))
    runs(p, text, bold=True)


def H3(text):
    p = doc.add_paragraph(style=STY("Heading 3"))
    runs(p, text, bold=True, italic=True)


def RUNIN(head, text):
    """APA level-4 style: bold run-in heading ending with a period, text follows."""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Inches(0.5)
    runs(p, head + ". ", bold=True)
    runs(p, text)


def BUL(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 2.0
    runs(p, text)


def pagebreak():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), color)
    tcPr.append(s)


def borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge, val in (("top", "single"), ("bottom", "single"), ("left", "nil"), ("right", "nil"),
                      ("insideH", "nil"), ("insideV", "nil")):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), val); e.set(qn("w:sz"), "8"); e.set(qn("w:color"), "000000")
        b.append(e)
    tblPr.append(b)


def cell_border_bottom(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    tb = OxmlElement("w:tcBorders"); e = OxmlElement("w:bottom")
    e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "6"); e.set(qn("w:color"), "000000")
    tb.append(e); tcPr.append(tb)


def caption(kind, num, title):
    p = doc.add_paragraph(); p.paragraph_format.keep_with_next = True
    p.paragraph_format.first_line_indent = Inches(0)
    runs(p, f"{kind} {num}", bold=True)
    p2 = doc.add_paragraph(); p2.paragraph_format.keep_with_next = True
    p2.paragraph_format.first_line_indent = Inches(0)
    runs(p2, title, italic=True)


def note(text):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.first_line_indent = Inches(0)
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.space_before = Pt(4)
    runs(p, "*Note.* " + text, size=10)


def TABLE(num, title, header, rows, widths, notes=None, size=9, bold_rows=(), align_num=True):
    caption("Table", num, title)
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    borders(t)
    tblPr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(int(sum(widths) * 1440))); tw.set(qn("w:type"), "dxa")
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tblPr.append(tw)
    grid = t._tbl.tblGrid
    for gc, wd in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(wd * 1440)))
    for j, h in enumerate(header):
        c = t.rows[0].cells[j]
        c.width = Inches(widths[j])
        c.paragraphs[0].paragraph_format.line_spacing = 1.0
        c.paragraphs[0].paragraph_format.first_line_indent = Inches(0)
        runs(c.paragraphs[0], h, size=size, bold=True)
        c.paragraphs[0].paragraph_format.keep_with_next = True
        cell_border_bottom(c)
    trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.rows[i + 1].cells[j]
            c.width = Inches(widths[j])
            pp = c.paragraphs[0]
            pp.paragraph_format.line_spacing = 1.0
            pp.paragraph_format.first_line_indent = Inches(0)
            pp.paragraph_format.space_before = Pt(1)
            pp.paragraph_format.space_after = Pt(1)
            runs(pp, str(v), size=size, bold=(i in bold_rows))
            if len(rows) <= 16 and i < len(rows) - 1:
                pp.paragraph_format.keep_with_next = True
            if i in bold_rows:
                shade(c, "EAF1FB")
    for r_ in t.rows:
        r_.cells[0]._tc.get_or_add_tcPr()
        trp = r_._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); trp.append(cs)
    if notes:
        note(notes)
    else:
        doc.add_paragraph().paragraph_format.line_spacing = 1.0


def FIGURE(num, title, path, width=6.0, notes=None):
    caption("Figure", num, title)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.first_line_indent = Inches(0)
    p.paragraph_format.keep_with_next = bool(notes)
    p.add_run().add_picture(str(path), width=Inches(width))
    if notes:
        note(notes)


def f2(x, d=2):
    s = f"{x:.{d}f}"
    return s


def nz(x, d=2):
    """APA: drop leading zero for statistics bounded by 1."""
    s = f"{x:.{d}f}"
    return s.replace("0.", ".", 1) if s.startswith("0.") else s.replace("-0.", "-.", 1)


def pval(p):
    return "< .001" if p < 0.001 else "= " + nz(p, 3)


exec(open(Path(__file__).with_name("report_content.py")).read())

out = ROOT / "outputs/final/Group3_QM640_Final_Report_ACEG.docx"
doc.save(out)
print("saved", out)
