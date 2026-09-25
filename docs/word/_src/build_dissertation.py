"""Builds the doctoral dissertation on the falcon-ocr-trans system as a .docx.

Run from the repository root:

    python docs/word/_src/build_dissertation.py

The document is built twice: the first pass records the labels of every
table, figure and equation (so that forward references such as "Table 9.3"
resolve), the second pass writes the file. Citations are numbered in order of
first appearance (IEEE style).

Integrity rule applied throughout: the system has not been benchmarked, so
every experimental result cell is the placeholder [TBD]. Only analytical
values (derived from formulas) and repository facts appear as numbers.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402

from docgen import Doc, INK, MUTED  # noqa: E402
from dissertation_parts import figures  # noqa: E402
from dissertation_parts.refs import REFS  # noqa: E402

REPO = HERE.parents[2]
OUT = REPO / "docs" / "word" / "Dissertation_Offline_Image_Translation.docx"
FIG_DIR = HERE / "figures" / "dissertation"

TBD = "[TBD]"

# Inline markup: **bold**, *italic*, `code`, _{subscript}, ^{superscript}
_RICH = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|_\{[^}]*\}|\^\{[^}]*\})")
_REF = re.compile(r"\{(T|F|E|S):([A-Za-z0-9_\-]+)\}")
_CITE = re.compile(r"\[@([A-Za-z0-9_,\s\-]+)\]")


class ThesisDoc(Doc):
    """Doc with subscript/superscript markup; everything else inherited."""

    def _caption(self, kind, label, text):
        """Caption with a literal chapter-based label ("Table 4.2").

        Doc._caption uses a SEQ field, which Word renumbers 1..n when it updates
        fields and would break chapter numbering. Here captions carry plain text in
        dedicated "Table Caption" / "Figure Caption" styles, and the lists of tables
        and figures are TOC fields over those styles (see list_of)."""
        para = self.d.add_paragraph(style=self._caption_style(kind))
        para.paragraph_format.keep_with_next = kind == "Table"
        self._fill(para, f"{kind} {label}. {text}")

    def _caption_style(self, kind):
        from docx.enum.style import WD_STYLE_TYPE
        name = f"{kind} Caption"
        styles = self.d.styles
        try:
            return styles[name]
        except KeyError:
            st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            st.base_style = styles["Caption"]
            st.quick_style = True
            return st

    def list_of(self, kind):
        from docgen import _add_field, ACCENT
        self._caption_style(kind)
        p = self.d.add_paragraph()
        r = p.add_run(f"List of {kind}s")
        r.font.size = Pt(17)
        r.font.bold = True
        r.font.color.rgb = ACCENT
        p = self.d.add_paragraph()
        _add_field(p.add_run(), f'TOC \\h \\z \\t "{kind} Caption,1"')
        self.page_break()

    def _fill(self, paragraph, text, *, bold=False, italic=False, size=None, color=None):
        for piece in _RICH.split(text or ""):
            if not piece:
                continue
            run_bold, run_italic, mono, sub, sup = bold, italic, False, False, False
            if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
                piece, run_bold = piece[2:-2], True
            elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
                piece, mono = piece[1:-1], True
            elif piece.startswith("_{") and piece.endswith("}"):
                piece, sub = piece[2:-1], True
            elif piece.startswith("^{") and piece.endswith("}"):
                piece, sup = piece[2:-1], True
            elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
                piece, run_italic = piece[1:-1], True
            run = paragraph.add_run(piece)
            run.bold = run_bold or None
            run.italic = run_italic or None
            if sub:
                run.font.subscript = True
            if sup:
                run.font.superscript = True
            if mono:
                run.font.name = "Consolas"
                run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Consolas")
                run.font.size = Pt((size or 11) - 1.5)
            elif size:
                run.font.size = Pt(size)
            if color is not None:
                run.font.color.rgb = color


class Ctx:
    """Writing context shared by all chapter modules."""

    def __init__(self, labels: dict, figs: dict):
        self.labels = labels
        self.figs = figs
        self.cite_order: list[str] = []
        self.eq_no = 0
        self.chap = ""
        self.sec = [0, 0]
        self.d = ThesisDoc(
            title="Offline Layout-Preserving Image Translation on Smartphones",
            body_font="Times New Roman", body_size=12, line_spacing=1.5,
            heading_font="Times New Roman", margins_cm=(2.5, 2.2, 2.5, 2.5))

    # ------------------------------------------------------------- references
    def cite(self, keys: str) -> str:
        nums = []
        for k in [k.strip() for k in keys.split(",") if k.strip()]:
            if k not in REFS:
                raise KeyError(f"unknown reference {k}")
            if k not in self.cite_order:
                self.cite_order.append(k)
            nums.append(self.cite_order.index(k) + 1)
        return ", ".join(f"[{n}]" for n in nums)

    def fmt(self, text: str) -> str:
        text = _CITE.sub(lambda m: self.cite(m.group(1)), text)

        def ref(m):
            kind, key = m.group(1), m.group(2)
            return self.labels.get(f"{kind}:{key}", "??")
        return _REF.sub(ref, text)

    # ------------------------------------------------------------------ text
    def chapter(self, n, title):
        self.d.page_break()
        self.chap = str(n)
        self.d.chapter(f"{n}.")
        self.eq_no = 0
        self.sec = [0, 0]
        self.d.h(1, f"Chapter {n}  {title}")

    def appendix(self, letter, title):
        self.d.page_break()
        self.chap = letter
        self.d.chapter(f"{letter}.")
        self.eq_no = 0
        self.sec = [0, 0]
        self.d.h(1, f"Appendix {letter}  {title}")

    def h2(self, title, key=None):
        self.sec[0] += 1
        self.sec[1] = 0
        num = f"{self.chap}.{self.sec[0]}"
        if key:
            self.labels[f"S:{key}"] = num
        self.d.h(2, f"{num}  {title}")

    def h3(self, title, key=None):
        self.sec[1] += 1
        num = f"{self.chap}.{self.sec[0]}.{self.sec[1]}"
        if key:
            self.labels[f"S:{key}"] = num
        self.d.h(3, f"{num}  {title}")

    def h4(self, title):
        self.d.h(4, title)

    def p(self, text, **kw):
        kw.setdefault("align", "justify")
        return self.d.p(self.fmt(text), **kw)

    def ps(self, *paras):
        for t in paras:
            self.p(t)

    def bullets(self, items, level=1):
        self.d.bullets([self.fmt(i) for i in items], level)

    def steps(self, items):
        self.d.steps([self.fmt(i) for i in items])

    def note(self, text, label="Note"):
        self.d.note(self.fmt(text), label)

    def code(self, text, size=8.5):
        self.d.code(text, size)

    def definition(self, kind, name, text):
        """Lemma / Proposition / Definition block, labelled per chapter."""
        para = self.d.d.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.left_indent = Cm(0.5)
        para.paragraph_format.right_indent = Cm(0.5)
        self.d._fill(para, self.fmt(f"**{kind} {name}.** ") + "")
        self.d._fill(para, self.fmt(text), italic=True)

    def proof(self, text):
        para = self.d.d.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.left_indent = Cm(0.5)
        para.paragraph_format.right_indent = Cm(0.5)
        self.d._fill(para, "*Proof.* " + self.fmt(text) + "  ∎")

    def eq(self, text, key=None):
        self.eq_no += 1
        num = f"{self.chap}.{self.eq_no}"
        if key:
            self.labels[f"E:{key}"] = num
        para = self.d.d.add_paragraph()
        para.paragraph_format.tab_stops.add_tab_stop(Cm(7.75), alignment=1)   # centre
        para.paragraph_format.tab_stops.add_tab_stop(Cm(15.5), alignment=2)  # right
        para.add_run("\t")
        before = len(para.runs)
        self.d._fill(para, text)
        for r in para.runs[before:]:
            if r.font.name != "Consolas":
                r.font.name = "Cambria Math"
                r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Cambria Math")
                r.font.size = Pt(11.5)
        para.add_run(f"\t({num})")
        return num

    # ---------------------------------------------------------- tables/figs
    def table(self, key, caption, headers, rows, widths=None, font_size=9, **kw):
        label = self.d.table([self.fmt(h) for h in headers],
                             [[self.fmt(str(c)) for c in r] for r in rows],
                             widths_cm=widths, caption=self.fmt(caption), font_size=font_size, **kw)
        self.labels[f"T:{key}"] = label
        return label

    def kv(self, key, caption, rows, widths=(4.6, 11.4)):
        label = self.d.kv_table([(self.fmt(a), self.fmt(b)) for a, b in rows],
                                caption=self.fmt(caption), widths_cm=widths)
        self.labels[f"T:{key}"] = label
        return label

    def figure(self, key, name, caption, width=15.0):
        label = self.d.figure(self.figs[name], self.fmt(caption), width_cm=width)
        self.labels[f"F:{key}"] = label
        return label


def build(labels: dict, figs: dict) -> Ctx:
    from dissertation_parts import (front, ch01, ch02, ch03, ch04, ch05, ch06,  # noqa: F401
                                    ch07, ch08, ch09, ch10, back)
    c = Ctx(labels, figs)
    front.build(c)
    for mod in (ch01, ch02, ch03, ch04, ch05, ch06, ch07, ch08, ch09, ch10):
        mod.build(c)
    back.build(c)
    return c


def main() -> None:
    figs = figures.build_all(FIG_DIR)
    labels: dict = {}
    build(labels, figs)            # pass 1: collect labels
    c = build(labels, figs)        # pass 2: resolve forward references
    out = c.d.save(OUT)
    print(f"wrote {out}")
    missing = [k for k in REFS if k not in c.cite_order]
    if missing:
        print(f"note: {len(missing)} registry entries not cited (omitted from list): {', '.join(missing)}")


if __name__ == "__main__":
    main()
