"""
Combine one or more chat messages (Modes 1-4) into a single downloadable PDF
or DOCX. Reuses the LaTeX-to-readable-text/diacritics-safety pipeline already
built for the Mode 5 exam PDF generator (bac_generator/pdf/pdf_generator.py)
instead of reimplementing math cleanup — same principle, applied to chat
transcripts instead of exam sheets.
"""

import re
from io import BytesIO

from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from bac_generator.pdf.pdf_generator import BOLD_FONT_NAME, FONT_NAME, clean_latex_for_pdf

ROLE_LABELS = {"user": "Întrebare", "assistant": "Răspuns AI"}

_TAG_RE = re.compile(r"</?(?:b|i|sup|sub|br/?)>")


def _split_paragraphs(content):
    """Blank-line paragraph splitting + '- '/'* ' bullet lines + **bold**/*italic*
    markdown -> inline tags. Not a full markdown parser, just enough for the
    plain markdown Gemini's replies come back as."""
    text = content.replace("\r\n", "\n").strip()
    for raw_para in re.split(r"\n\s*\n", text):
        lines = []
        for line in raw_para.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                stripped = "• " + stripped[2:]
            if stripped:
                lines.append(stripped)
        if not lines:
            continue
        joined = "<br/>".join(lines)
        joined = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", joined)
        joined = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", joined)
        yield joined


def _message_header(msg):
    label = ROLE_LABELS.get(msg["role"], msg["role"])
    stamp = msg.get("created_at")
    return label if not stamp else f"{label} — {stamp.strftime('%d.%m.%Y %H:%M')}"


def build_messages_pdf(title, messages):
    """messages: iterable of {"role", "content", "created_at"} dicts, oldest
    first. Returns PDF bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ExportTitle", parent=styles["Title"], fontName=BOLD_FONT_NAME, fontSize=18, spaceAfter=18,
    )
    role_style = ParagraphStyle(
        "ExportRole", parent=styles["Normal"], fontName=BOLD_FONT_NAME, fontSize=11,
        textColor="#0f172a", spaceBefore=14, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "ExportBody", parent=styles["Normal"], fontName=FONT_NAME, fontSize=10.5, leading=15,
    )

    story = [Paragraph(clean_latex_for_pdf(title), title_style), Spacer(1, 6)]
    for msg in messages:
        story.append(Paragraph(clean_latex_for_pdf(_message_header(msg)), role_style))
        for para in _split_paragraphs(msg["content"]):
            story.append(Paragraph(clean_latex_for_pdf(para), body_style))
            story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def build_messages_docx(title, messages):
    """Same content/order as build_messages_pdf, as a .docx file.

    HONEST LIMITATION: bold/italic/sup/sub markup and LaTeX cleanup both run
    through the same clean_latex_for_pdf() used for the PDF, then the HTML-ish
    tags it emits for ReportLab are stripped back to plain text here rather
    than converted into per-run DOCX formatting - content and readability are
    correct, but bold/italic emphasis isn't preserved in the .docx output."""
    document = DocxDocument()
    document.add_heading(title, level=1)

    for msg in messages:
        heading = document.add_paragraph()
        run = heading.add_run(_message_header(msg))
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

        for para in _split_paragraphs(msg["content"]):
            cleaned = _TAG_RE.sub(" ", clean_latex_for_pdf(para))
            cleaned = (
                cleaned.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            )
            cleaned = re.sub(r" {2,}", " ", cleaned).strip()
            if cleaned:
                document.add_paragraph(cleaned)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
