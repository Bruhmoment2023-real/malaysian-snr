"""Small helpers to build the v17 manuscript/appendix on the v16 Word template (styles kept: Heading 1-3, kw, Normal (Web), cap, note, ref)."""
import copy, re
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

TEMPLATE = r"C:/Users/seans/Research-Publishing-fallback/submission-v16/02_malaysian_snr_DigitalFinance/02_manuscript.docx"
APPX_TEMPLATE = r"C:/Users/seans/Research-Publishing-fallback/submission-v16/02_malaysian_snr_DigitalFinance/02_online_appendix.docx"


def new_doc(template=TEMPLATE):
    d = docx.Document(template)
    body = d.element.body
    for ch in list(body):
        if ch.tag.endswith("sectPr"):
            continue
        body.remove(ch)
    return d


def _style(d, name):
    return d.styles[name]


def add(d, style, text, bold_prefix=None):
    p = d.add_paragraph(style=style)
    if bold_prefix:
        r = p.add_run(bold_prefix); r.bold = True
    # *italic* spans
    parts = re.split(r"(\*[^*]+\*)", text)
    for part in parts:
        if part.startswith("*") and part.endswith("*") and len(part) > 2:
            r = p.add_run(part[1:-1]); r.italic = True
        elif part:
            p.add_run(part)
    return p


def h1(d, t): return add(d, "Heading 1", t)
def h2(d, t): return add(d, "Heading 2", t)
def h3(d, t): return add(d, "Heading 3", t)
def para(d, t): return add(d, "Normal (Web)", t)
def kw(d, t): return add(d, "kw", t)
def cap(d, t): return add(d, "cap", t)
def note(d, t): return add(d, "note", t)
def ref(d, t): return add(d, "ref", t)


def picture(d, path, width=6.2):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    return p


def _border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for edge, val in kw.items():
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), val); e.set(qn("w:sz"), "6"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "000000")
        b.append(e)
    tcPr.append(b)


def table(d, header, rows, widths=None, size=7.5, align_first_left=True):
    t = d.add_table(rows=1 + len(rows), cols=len(header))
    t.autofit = True
    for j, h in enumerate(header):
        c = t.rows[0].cells[j]; c.text = ""
        r = c.paragraphs[0].add_run(str(h)); r.bold = True; r.font.size = Pt(size)
        _border(c, top="single", bottom="single")
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            c = t.rows[i].cells[j]; c.text = ""
            p = c.paragraphs[0]
            r = p.add_run(str(v)); r.font.size = Pt(size)
            if j > 0 or not align_first_left:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if re.match(r"^[+\-−]?[\d.,%]", str(v)) else WD_ALIGN_PARAGRAPH.LEFT
            if i == len(rows):
                _border(c, bottom="single")
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
    if not widths:
        widths = [6.3 / len(header)] * len(header)
    t.autofit = False
    if widths:
        for row in t.rows:
            for j, w in enumerate(widths):
                row.cells[j].width = Inches(w)
    return t


def md_table_rows(md_lines):
    """Parse a markdown pipe table (list of lines) -> header, rows."""
    cells = [[c.strip().replace("**", "") for c in ln.strip().strip("|").split("|")] for ln in md_lines if ln.strip().startswith("|")]
    header = cells[0]; rows = [r for r in cells[2:]]
    return header, rows
