"""
Turn one or more AI replies (Modes 1-4) into a printable worksheet - PDF or
DOCX - rather than a dump of the chat.

What the teacher hands to a class is a *fișă de lucru*: an optional header
(title, type, class, teacher, date), then numbered exercises. It is never a
transcript, so nothing here emits "Răspuns AI", timestamps or the teacher's
own prompts. When several replies are exported together each one becomes a
numbered section ("Subiectul I", "Subiectul II", ...), which is how a teacher
builds a two-row test or a multi-subject sheet out of one conversation.

LaTeX cleanup is shared with the Mode 5 exam PDF generator
(bac_generator/pdf/pdf_generator.py) instead of being reimplemented.
"""

import re
from datetime import date
from io import BytesIO

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from bac_generator.pdf.pdf_generator import BOLD_FONT_NAME, FONT_NAME, clean_latex_for_pdf

# The purposes a sheet can be printed for. The key is what the form posts, the
# value is what gets printed under the title.
SHEET_TYPES = {
    "": "",
    "tema": "Temă",
    "clasa": "Exerciții în clasă",
    "test_r1": "Test — Rândul 1",
    "test_r2": "Test — Rândul 2",
    "fisa": "Fișă de lucru",
    "evaluare": "Evaluare",
    "recapitulare": "Recapitulare",
}

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
         "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

# "1. ", "2) ", "12 - " at the start of a line: the model is told to number its
# exercises, so when it already did we renumber from that instead of adding a
# second number in front of the first.
_NUMBERED_RE = re.compile(r"^\s*(\d{1,3})\s*[.)\-]\s+(.*)$", re.S)

# "a)", "b.", "(c)" - subpoints stay attached to the exercise above them.
_SUBPOINT_RE = re.compile(r"^\s*\(?([a-hA-H])\)\s+|^\s*([a-hA-H])[.)]\s+")

_BULLET_RE = re.compile(r"^\s*[-*•]\s+")


def _roman(n):
    return ROMAN[n - 1] if 1 <= n <= len(ROMAN) else str(n)


def _inline_markdown(text):
    """**bold** / *italic* -> the tag subset ReportLab's Paragraph understands."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _strip_markdown_headings(line):
    """The chat renders '### Titlu' as a heading; on a worksheet it is noise."""
    return re.sub(r"^\s*#{1,6}\s*", "", line)


def split_exercises(content):
    """Split one AI reply into the items that should be printed.

    Returns a list of (kind, text) where kind is:
      "exercise" - a numbered exercise (text has any existing number stripped)
      "sub"      - a subpoint belonging to the exercise above it
      "bullet"   - a bullet line
      "text"     - prose that is not an exercise (intros, notes, explanations)

    Numbering is deliberately NOT invented for prose: a long Mode-1 explanation
    stays prose, while the one-exercise-per-line output Mode 2 produces becomes
    exercises. The signal is whether the model already numbered the line, or
    whether the reply is a list of short standalone lines.
    """
    text = (content or "").replace("\r\n", "\n").strip()
    if not text:
        return []

    raw_blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]

    # A reply where the model numbered things is unambiguous. Otherwise, treat
    # it as a list of exercises only if every line is short and standalone -
    # which is exactly the "$\int x dx$" / "$\begin{pmatrix}...$" shape Mode 2
    # returns, and never the shape a prose answer has.
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    any_numbered = any(_NUMBERED_RE.match(l) for l in lines)
    looks_like_list = (
        not any_numbered
        and len(lines) > 1
        and all(len(l) <= 200 and not l.endswith(".") for l in lines)
    )

    items = []
    for block in raw_blocks:
        for line in block.split("\n"):
            line = _strip_markdown_headings(line.strip())
            if not line:
                continue

            numbered = _NUMBERED_RE.match(line)
            if numbered:
                items.append(("exercise", numbered.group(2).strip()))
                continue

            if _SUBPOINT_RE.match(line):
                items.append(("sub", line))
                continue

            if _BULLET_RE.match(line):
                items.append(("bullet", _BULLET_RE.sub("", line)))
                continue

            items.append(("exercise" if looks_like_list else "text", line))

    return items


def _render(text):
    """LaTeX -> the small markup subset both back ends understand
    (<b> <i> <sup> <sub> <br/>).

    clean_latex_for_pdf emits real newlines for matrices and cases, so those
    are kept as <br/> - otherwise a 2x2 matrix prints as one flat line.
    """
    cleaned = clean_latex_for_pdf(_inline_markdown(text)).strip()
    # A matrix ends on a newline, but the punctuation that closes the
    # surrounding sentence belongs to the last row, not to a line of its own
    # ("[1 0]" then "." on the next line is how the old export looked).
    cleaned = re.sub(r"\n[ \t]*([.,;:!?)\]])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]*\n[ \t]*", "<br/>", cleaned)
    # \, and friends leave runs of spaces behind once stripped.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return re.sub(r"(?:<br/>)+$", "", cleaned)


_RUN_RE = re.compile(r"<(/?)(b|i|sup|sub)>|<br\s*/?>")
_ENTITIES = (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&amp;", "&"))


def _unescape(text):
    for entity, char in _ENTITIES:
        text = text.replace(entity, char)
    return text


def _runs(text):
    """Split rendered markup into lines of (text, flags) runs.

    DOCX gets real superscript/subscript/bold runs out of this. Flattening the
    tags to plain text instead is what turned an integral with limits into the
    unreadable "∫15 x2 ex dx".
    """
    markup = _render(text)
    lines = [[]]
    stack = []
    pos = 0

    for match in _RUN_RE.finditer(markup):
        chunk = markup[pos:match.start()]
        if chunk:
            lines[-1].append((_unescape(chunk), tuple(stack)))
        pos = match.end()

        tag = match.group(2)
        if tag is None:                      # <br/>
            lines.append([])
        elif match.group(1):                 # closing tag
            if tag in stack:
                stack.reverse()
                stack.remove(tag)
                stack.reverse()
        else:
            stack.append(tag)

    chunk = markup[pos:]
    if chunk:
        lines[-1].append((_unescape(chunk), tuple(stack)))

    return [line for line in lines if any(t.strip() for t, _ in line)]


def _add_runs(paragraph, line, bold_all=False):
    for text, flags in line:
        run = paragraph.add_run(text)
        run.bold = bold_all or ("b" in flags)
        run.italic = "i" in flags
        run.font.superscript = "sup" in flags
        run.font.subscript = "sub" in flags


def _header_lines(meta):
    """The subtitle lines under the title: type, class, teacher, date."""
    meta = meta or {}
    sheet_type = SHEET_TYPES.get((meta.get("sheet_type") or "").strip(), "")

    left = [part for part in (sheet_type, (meta.get("school_class") or "").strip()) if part]
    right = []
    if (meta.get("teacher") or "").strip():
        right.append(meta["teacher"].strip())
    if meta.get("include_date"):
        right.append(date.today().strftime("%d.%m.%Y"))

    lines = []
    if left:
        lines.append(" · ".join(left))
    if right:
        lines.append(" · ".join(right))
    return lines


def _sections(messages, meta):
    """Group the selected replies into (label, items) sections.

    One reply -> no section heading at all, the exercises start straight away.
    Several replies -> "Subiectul I/II/..." headings, unless the teacher turned
    them off, in which case the exercises simply run on with continuous
    numbering.
    """
    meta = meta or {}
    use_sections = bool(meta.get("sections")) and len(messages) > 1

    sections = []
    for index, msg in enumerate(messages, start=1):
        items = split_exercises(msg["content"])
        if not items:
            continue
        label = f"Subiectul {_roman(index)}" if use_sections else None
        sections.append((label, items))
    return sections


# =========================================================
# PDF
# =========================================================

def build_messages_pdf(title, messages, meta=None):
    """messages: iterable of {"role", "content", ...} dicts, oldest first.
    meta: the worksheet header the teacher filled in (see _header_lines) plus
    "numbering" and "sections" flags. Returns PDF bytes."""
    meta = meta or {}
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
        title=title or "Fișă de lucru",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SheetTitle", parent=styles["Title"], fontName=BOLD_FONT_NAME,
        fontSize=17, spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "SheetMeta", parent=styles["Normal"], fontName=FONT_NAME, fontSize=10,
        textColor="#475569", alignment=1, spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "SheetSection", parent=styles["Normal"], fontName=BOLD_FONT_NAME,
        fontSize=12.5, textColor="#0f172a", spaceBefore=16, spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "SheetBody", parent=styles["Normal"], fontName=FONT_NAME,
        fontSize=11, leading=17, spaceAfter=8,
    )
    exercise_style = ParagraphStyle(
        "SheetExercise", parent=body_style, leftIndent=18, firstLineIndent=-18,
        spaceAfter=10,
    )
    sub_style = ParagraphStyle("SheetSub", parent=body_style, leftIndent=36, spaceAfter=4)

    story = []

    clean_title = (title or "").strip()
    if clean_title:
        story.append(Paragraph(_render(clean_title), title_style))
    for line in _header_lines(meta):
        story.append(Paragraph(_render(line), meta_style))
    if clean_title or _header_lines(meta):
        story.append(Spacer(1, 14))

    number_them = meta.get("numbering", True)
    counter = 0

    for label, items in _sections(messages, meta):
        if label:
            story.append(Paragraph(label, section_style))
            if meta.get("restart_numbering"):
                counter = 0

        for kind, text in items:
            rendered = _render(text)
            if not rendered:
                continue
            if kind == "exercise":
                counter += 1
                prefix = f"<b>{counter}.</b> " if number_them else ""
                story.append(Paragraph(prefix + rendered, exercise_style))
            elif kind == "sub":
                story.append(Paragraph(rendered, sub_style))
            elif kind == "bullet":
                story.append(Paragraph("• " + rendered, sub_style))
            else:
                story.append(Paragraph(rendered, body_style))

    if not story:
        story.append(Paragraph("Nimic de exportat.", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# DOCX
# =========================================================

def build_messages_docx(title, messages, meta=None):
    """Same worksheet as build_messages_pdf, as an editable .docx.

    HONEST LIMITATION: inline **bold**/*italic* emphasis inside an exercise is
    flattened to plain text here - superscripts, subscripts and matrix line
    breaks survive, per-run emphasis does not. Exercise numbers and section
    headings are real formatting, so the teacher can edit the sheet in Word.
    """
    meta = meta or {}
    document = DocxDocument()

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)

    clean_title = (title or "").strip()
    if clean_title:
        heading = document.add_paragraph()
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = heading.add_run(clean_title)
        run.bold = True
        run.font.size = Pt(16)

    for line in _header_lines(meta):
        para = document.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(line)
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    number_them = meta.get("numbering", True)
    counter = 0
    wrote_anything = False

    for label, items in _sections(messages, meta):
        if label:
            para = document.add_paragraph()
            run = para.add_run(label)
            run.bold = True
            run.font.size = Pt(13)
            if meta.get("restart_numbering"):
                counter = 0

        for kind, text in items:
            lines = _runs(text)
            if not lines:
                continue
            wrote_anything = True

            if kind == "exercise":
                counter += 1
                para = document.add_paragraph()
                para.paragraph_format.left_indent = Pt(18)
                para.paragraph_format.first_line_indent = Pt(-18)
                if number_them:
                    number_run = para.add_run(f"{counter}. ")
                    number_run.bold = True
                _add_runs(para, lines[0])
                # Matrix rows and other hard-broken lines stay with their
                # exercise, indented under it.
                for extra in lines[1:]:
                    cont = document.add_paragraph()
                    cont.paragraph_format.left_indent = Pt(36)
                    _add_runs(cont, extra)
            elif kind in ("sub", "bullet"):
                para = document.add_paragraph()
                para.paragraph_format.left_indent = Pt(36)
                if kind == "bullet":
                    para.add_run("• ")
                for index, line in enumerate(lines):
                    if index:
                        para.add_run(" ")
                    _add_runs(para, line)
            else:
                for line in lines:
                    _add_runs(document.add_paragraph(), line)

    if not wrote_anything and not clean_title:
        document.add_paragraph("Nimic de exportat.")

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
