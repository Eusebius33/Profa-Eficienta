import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Try to register LiberationSerif and DejaVuSans fonts to support Romanian diacritics and mathematical Unicode symbols
FONT_NAME = "Helvetica"
BOLD_FONT_NAME = "Helvetica-Bold"
ITALIC_FONT_NAME = "Helvetica-Oblique"

current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "..", "..", "static", "fonts")
local_fonts = {
    "LiberationSerif": os.path.join(static_dir, "LiberationSerif-Regular.ttf"),
    "LiberationSerif-Bold": os.path.join(static_dir, "LiberationSerif-Bold.ttf"),
    "LiberationSerif-Italic": os.path.join(static_dir, "LiberationSerif-Italic.ttf"),
    "DejaVuSans": os.path.join(static_dir, "DejaVuSans.ttf"),
    "DejaVuSans-Bold": os.path.join(static_dir, "DejaVuSans-Bold.ttf")
}

fonts_registered = False
dejavu_registered = False

try:
    if os.path.exists(local_fonts["LiberationSerif"]):
        pdfmetrics.registerFont(TTFont("LiberationSerif", local_fonts["LiberationSerif"]))
        pdfmetrics.registerFont(TTFont("LiberationSerif-Bold", local_fonts["LiberationSerif-Bold"]))
        pdfmetrics.registerFont(TTFont("LiberationSerif-Italic", local_fonts["LiberationSerif-Italic"]))
        FONT_NAME = "LiberationSerif"
        BOLD_FONT_NAME = "LiberationSerif-Bold"
        ITALIC_FONT_NAME = "LiberationSerif-Italic"
        fonts_registered = True
except Exception:
    pass

try:
    if os.path.exists(local_fonts["DejaVuSans"]):
        pdfmetrics.registerFont(TTFont("DejaVuSans", local_fonts["DejaVuSans"]))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", local_fonts["DejaVuSans-Bold"]))
        dejavu_registered = True
except Exception:
    pass

def strip_diacritics(text: str) -> str:
    """
    Fallback cleaner: replaces Romanian diacritics with standard English counterparts
    to prevent encoding/rendering errors on systems without the registered font.
    """
    replacements = {
        'ă': 'a', 'Ă': 'A',
        'â': 'a', 'Â': 'A',
        'î': 'i', 'Î': 'I',
        'ș': 's', 'Ș': 'S',
        'ț': 't', 'Ț': 'T',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

def escape_xml_tags(text: str) -> str:
    """
    Escapes &, <, and > in text for ReportLab Paragraph, except for allowed HTML formatting tags:
    <b>, </b>, <i>, </i>, <br/>, <br>, <sup>, </sup>, <sub>, </sub>, <font ...>, </font>
    """
    if not text:
        return ""
        
    # Replace valid tags with placeholders
    text = text.replace("<b>", "__B_OPEN__")
    text = text.replace("</b>", "__B_CLOSE__")
    text = text.replace("<i>", "__I_OPEN__")
    text = text.replace("</i>", "__I_CLOSE__")
    text = text.replace("<sup>", "__SUP_OPEN__")
    text = text.replace("</sup>", "__SUP_CLOSE__")
    text = text.replace("<sub>", "__SUB_OPEN__")
    text = text.replace("</sub>", "__SUB_CLOSE__")
    text = text.replace("<br/>", "__BR__")
    text = text.replace("<br>", "__BR__")
    text = text.replace("</font>", "__FONT_CLOSE__")
    text = re.sub(r'<font\s+name="([^"]+)">', r'__FONT_OPEN_\1__', text)
    
    # Escape all other <, >, and &
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    
    # Restore valid tags
    text = text.replace("__B_OPEN__", "<b>")
    text = text.replace("__B_CLOSE__", "</b>")
    text = text.replace("__I_OPEN__", "<i>")
    text = text.replace("__I_CLOSE__", "</i>")
    text = text.replace("__SUP_OPEN__", "<sup>")
    text = text.replace("__SUP_CLOSE__", "</sup>")
    text = text.replace("__SUB_OPEN__", "<sub>")
    text = text.replace("__SUB_CLOSE__", "</sub>")
    text = text.replace("__BR__", "<br/>")
    text = text.replace("__FONT_CLOSE__", "</font>")
    text = re.sub(r'__FONT_OPEN_([^_\s]+)__', r'<font name="\1">', text)
    
    return text

def format_matrix(match):
    matrix_body = match.group(1)
    matrix_body = clean_latex_for_pdf(matrix_body)
    rows = [r.strip() for r in matrix_body.split(r'\\') if r.strip()]
    grid = []
    for r in rows:
        cols = [c.strip() for c in re.split(r'&(?:amp;)?', r)]
        grid.append(cols)
    if not grid:
        return ""
    num_cols = max(len(row) for row in grid)
    col_widths = [0] * num_cols
    for row in grid:
        for i, col in enumerate(row):
            col_widths[i] = max(col_widths[i], len(col))
    formatted_rows = []
    for row in grid:
        padded_cols = []
        for i, col in enumerate(row):
            padded = col.ljust(col_widths[i])
            padded_cols.append(padded)
        for i in range(len(row), num_cols):
            padded_cols.append(" " * col_widths[i])
        formatted_rows.append("&nbsp;&nbsp;".join(padded_cols))
    final_rows = []
    for r in formatted_rows:
        final_rows.append(f"[&nbsp;{r}&nbsp;]")
    matrix_str = "<br/>" + "<br/>".join(final_rows) + "<br/>"
    return f'<font name="Courier">{matrix_str}</font>'

def format_vmatrix(match):
    matrix_body = match.group(1)
    matrix_body = clean_latex_for_pdf(matrix_body)
    rows = [r.strip() for r in matrix_body.split(r'\\') if r.strip()]
    grid = []
    for r in rows:
        cols = [c.strip() for c in re.split(r'&(?:amp;)?', r)]
        grid.append(cols)
    if not grid:
        return ""
    num_cols = max(len(row) for row in grid)
    col_widths = [0] * num_cols
    for row in grid:
        for i, col in enumerate(row):
            col_widths[i] = max(col_widths[i], len(col))
    formatted_rows = []
    for row in grid:
        padded_cols = []
        for i, col in enumerate(row):
            padded = col.ljust(col_widths[i])
            padded_cols.append(padded)
        for i in range(len(row), num_cols):
            padded_cols.append(" " * col_widths[i])
        formatted_rows.append("&nbsp;&nbsp;".join(padded_cols))
    final_rows = []
    for r in formatted_rows:
        final_rows.append(f"|&nbsp;{r}&nbsp;|")
    matrix_str = "<br/>" + "<br/>".join(final_rows) + "<br/>"
    return f'<font name="Courier">{matrix_str}</font>'

def format_cases(match):
    cases_body = match.group(1)
    cases_body = clean_latex_for_pdf(cases_body)
    rows = [r.strip() for r in cases_body.split(r'\\') if r.strip()]
    formatted_rows = []
    for r in rows:
        cols = [c.strip() for c in re.split(r'&(?:amp;)?', r)]
        formatted_rows.append("{&nbsp;" + ",&nbsp;&nbsp;".join(cols))
    cases_str = "<br/>" + "<br/>".join(formatted_rows) + "<br/>"
    return f'<font name="Courier">{cases_str}</font>'

def clean_latex_for_pdf(text: str) -> str:
    """
    Converts LaTeX formulas into clean, readable text/unicode/HTML representation for ReportLab.
    """
    if not text:
        return ""
        
    # Normalize Windows newlines to Unix newlines
    text = text.replace('\r\n', '\n')
    
    # Normalize \dfrac to \frac
    text = text.replace(r"\dfrac", r"\frac")
    
    # Clean text environment
    text = re.sub(r'\\text\s*\{([^}]*)\}', r'\1', text)
    
    # Strip \left and \right
    text = text.replace(r"\left", "")
    text = text.replace(r"\right", "")
    
    # Strip literal braces
    text = text.replace(r"\{", "{")
    text = text.replace(r"\}", "}")
        
    # Replace common LaTeX structures with text/Unicode
    text = text.replace(r"\mathbb{R}", "ℝ")
    text = text.replace(r"\mathbb{N}", "ℕ")
    text = text.replace(r"\mathbb{Z}", "ℤ")
    text = text.replace(r"\mathbb{Q}", "ℚ")
    text = text.replace(r"\mathbb{C}", "ℂ")
    text = text.replace(r"\iff", " ⇔ ")
    text = text.replace(r"\Leftrightarrow", " ⇔ ")
    text = text.replace(r"\Rightarrow", " ⇒ ")
    text = text.replace(r"\to", " → ")
    text = text.replace(r"\rightarrow", " → ")
    text = text.replace(r"\leftrightarrow", " ↔ ")
    text = text.replace(r"\notin", " ∉ ")
    text = text.replace(r"\in", " ∈ ")
    text = text.replace(r"\subset", " ⊂ ")
    text = text.replace(r"\subseteq", " ⊆ ")
    text = text.replace(r"\infty", "∞")
    text = text.replace(r"\det", "det")
    text = text.replace(r"\text{tr}", "tr")
    
    # Greek letters
    text = text.replace(r"\lambda", "λ")
    text = text.replace(r"\Delta", "Δ")
    text = text.replace(r"\alpha", "α")
    text = text.replace(r"\beta", "β")
    text = text.replace(r"\gamma", "γ")
    text = text.replace(r"\omega", "ω")
    text = text.replace(r"\sigma", "σ")
    text = text.replace(r"\mu", "μ")
    text = text.replace(r"\rho", "ρ")
    text = text.replace(r"\phi", "φ")
    text = text.replace(r"\pi", "π")
    text = text.replace(r"\theta", "θ")
    
    # Inequalities
    text = text.replace(r"\geq", " ≥ ")
    text = text.replace(r"\leq", " ≤ ")
    text = text.replace(r"\ge", " ≥ ")
    text = text.replace(r"\le", " ≤ ")
    text = text.replace(r"\neq", " ≠ ")
    text = text.replace(r"\lt", " < ")
    text = text.replace(r"\gt", " > ")
    
    # Operations
    text = text.replace(r"\pm", " ± ")
    text = text.replace(r"\dots", "...")
    text = text.replace(r"\cdot", "·")
    text = text.replace(r"\times", " × ")
    text = text.replace(r"\setminus", " ∖ ")
    text = text.replace(r"\cap", " ∩ ")
    text = text.replace(r"\cup", " ∪ ")
    text = text.replace(r"^\circ", "°")
    text = text.replace(r"\_", "_")
    text = text.replace(r"\,", " ")
    
    text = text.replace(r"\hat{A}", "A")
    text = text.replace(r"\hat{B}", "B")
    text = text.replace(r"\hat{C}", "C")
    
    # Trigonometry & logs
    text = text.replace(r"\sin", "sin")
    text = text.replace(r"\cos", "cos")
    text = text.replace(r"\tan", "tan")
    text = text.replace(r"\cot", "cot")
    text = text.replace(r"\arcsin", "arcsin")
    text = text.replace(r"\arccos", "arccos")
    text = text.replace(r"\arctan", "arctan")
    text = text.replace(r"\log", "log")
    text = text.replace(r"\lg", "lg")
    text = text.replace(r"\ln", "ln")
    
    # Sum / Prod / Int / Limit
    text = text.replace(r"\sum", "∑")
    text = text.replace(r"\prod", "∏")
    text = text.replace(r"\iint", "∬")
    text = text.replace(r"\int", "∫")
    text = text.replace(r"\lim", "lim")
    text = text.replace(r"\partial", "∂")
    
    # Vectors
    text = re.sub(r'\\vec\{([^}]*)\}', r'\1⃗', text)
    
    # Fractions
    def format_fraction(match):
        num = match.group(1).strip()
        den = match.group(2).strip()
        if re.match(r'^[a-zA-Z0-9]+$', num) and re.match(r'^[a-zA-Z0-9]+$', den):
            return f"{num}/{den}"
        return f"({num})/({den})"
        
    for _ in range(5):
        if r"\frac" not in text:
            break
        text = re.sub(r'\\frac\s*\{([^}]*)\}\s*\{([^}]*)\}', format_fraction, text)
        
    # Roots
    for _ in range(5):
        if r"\sqrt" not in text:
            break
        text = re.sub(r'\\sqrt\s*\[([^\]]*)\]\s*\{([^}]*)\}', r'<sup>\1</sup>√(\2)', text)
        text = re.sub(r'\\sqrt\s*\{([^}]*)\}', r'√(\1)', text)
        
    # Binomial / Combinations
    text = re.sub(r'\\binom\s*\{([^}]*)\}\s*\{([^}]*)\}', r'C(\1, \2)', text)
    
    # Format environments
    text = re.sub(r'\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}', format_matrix, text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{vmatrix\}(.*?)\\end\{vmatrix\}', format_vmatrix, text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{cases\}(.*?)\\end\{cases\}', format_cases, text, flags=re.DOTALL)
    
    # Clean up double "dacă dacă"
    text = re.sub(r'\bdacă\s+dacă\b', 'dacă', text)
    text = re.sub(r'\bdaca\s+daca\b', 'daca', text)

    # Superscripts and subscripts
    text = re.sub(r'\^\{([^}]*)\}', r'<sup>\1</sup>', text)
    text = re.sub(r'\_\{([^}]*)\}', r'<sub>\1</sub>', text)
    text = re.sub(r'\^([a-zA-Z0-9+-])', r'<sup>\1</sup>', text)
    text = re.sub(r'\_([a-zA-Z0-9])', r'<sub>\1</sub>', text)

    # Strip inline and display math dollars
    text = text.replace("$$", "\n")
    text = text.replace("$", "")
    
    # Wrap mathematical symbols in DejaVuSans if registered
    if dejavu_registered:
        math_symbols = [
            'ℝ', 'ℤ', 'ℚ', 'ℕ', 'ℂ', 'λ', 'π', 'θ', 'Δ', 'α', 'β', 'γ', 'ω', 'σ', 'μ', 'ρ', 'φ',
            '∫', '∬', '∂', '∞', '≤', '≥', '≠', '∈', '∉', '⊂', '⊆', '√', '∑', '∏', '→', '↔', '⇔', '⇒',
            '±', '×', '∩', '∪', '·', '°', '∖', '⃗'
        ]
        for sym in math_symbols:
            text = text.replace(sym, f'<font name="DejaVuSans">{sym}</font>')
    
    # Strip diacritics if fonts aren't registered
    if not fonts_registered:
        text = strip_diacritics(text)
        
    # Escape XML/HTML special characters
    text = escape_xml_tags(text)
        
    return text

def get_spec_details(bac: str):
    bac = str(bac).upper()
    if bac == "M1":
        return {
            "title": "Matematică M_mate-info",
            "filiera": "Filiera teoretică, profilul real, specializarea matematică-informatică"
        }
    elif bac == "M2":
        return {
            "title": "Matematică M_şt-nat",
            "filiera": "Filiera teoretică, profilul real, specializarea științe ale naturii"
        }
    elif bac == "M4":
        return {
            "title": "Matematică M_pedagogic",
            "filiera": "Filiera vocațională, profilul pedagogic, specializarea învățător-educatoare"
        }
    else: # Default is M3 (M_tehnologic)
        return {
            "title": "Matematică M_tehnologic",
            "filiera": "Filiera tehnologică: profilul servicii, resurse naturale și protecția mediului, profilul tehnic"
        }

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.bac = "M3"

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Determine the font
        font_name = FONT_NAME if fonts_registered else "Helvetica"
        
        # 1. Page Numbering
        self.setFont(font_name, 9)
        self.setFillColor(colors.HexColor('#64748B'))
        page_text = f"Pagina {self._pageNumber} din {page_count}"
        self.drawCentredString(A4[0] / 2.0, 30, page_text)
        
        # 2. Left side footer: "Probă scrisă la matematică [Specializare]"
        spec_info = get_spec_details(self.bac)
        self.drawString(42.5, 30, f"Probă scrisă la matematică {spec_info['title']}")
        
        # Draw a thin horizontal rule above the footer
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.5)
        self.line(42.5, 45, A4[0] - 42.5, 45)
        
        self.restoreState()

def make_numbered_canvas(bac_code):
    class CustomNumberedCanvas(NumberedCanvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.bac = bac_code
    return CustomNumberedCanvas

def build_pdf(filepath: str, exam_data: dict, include_solutions: bool = False, bac: str = "M3"):
    """
    Builds a professional PDF file for the generated BAC exam.
    """
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=42.5,
        leftMargin=42.5,
        topMargin=42.5,
        bottomMargin=42.5
    )
    
    styles = getSampleStyleSheet()
    
    # Custom typography (using LiberationSerif if registered)
    style_normal = ParagraphStyle(
        'BacNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1E293B')
    )
    
    style_bold = ParagraphStyle(
        'BacBold',
        parent=style_normal,
        fontName=BOLD_FONT_NAME
    )
    
    style_italic = ParagraphStyle(
        'BacItalic',
        parent=style_normal,
        fontName=ITALIC_FONT_NAME
    )
    
    style_header_title = ParagraphStyle(
        'BacHeaderTitle',
        parent=style_normal,
        fontName=BOLD_FONT_NAME,
        fontSize=12,
        leading=16,
        alignment=1, # Center
        textColor=colors.HexColor('#0F172A')
    )
    
    style_header_subtitle = ParagraphStyle(
        'BacHeaderSub',
        parent=style_normal,
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#0F172A')
    )
    
    style_section_title = ParagraphStyle(
        'BacSectionTitle',
        parent=style_normal,
        fontName=BOLD_FONT_NAME,
        fontSize=12,
        leading=16,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor('#0F172A')
    )
    
    story = []
    
    # 1. Centered Header
    story.append(Paragraph("<b>Ministerul Educației</b>", style_header_title))
    story.append(Paragraph("Centrul Național de Politici și Evaluare în Educație", style_header_subtitle))
    story.append(Spacer(1, 6))
    
    # Draw a thin horizontal divider line below the header
    divider = Table([[""]], colWidths=[A4[0] - 2 * 42.5])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.75, colors.HexColor('#0F172A')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 10))
    
    spec_info = get_spec_details(bac)
    title_suffix = " - BAREM DE EVALUARE ȘI DE NOTARE" if include_solutions else ""
    
    story.append(Paragraph(f"<b>Examenul național de bacalaureat 2026</b>{title_suffix}", style_header_title))
    story.append(Paragraph("<b>Proba E. c)</b>", style_header_title))
    story.append(Paragraph(f"<b>{spec_info['title']}</b>", style_header_title))
    story.append(Spacer(1, 4))
    
    # Subtitle filiera
    story.append(Paragraph(f"<i>{spec_info['filiera']}</i>", style_header_subtitle))
    story.append(Spacer(1, 12))
    
    # General instructions box
    instr_text = (
        "• Toate subiectele sunt obligatorii. Se acordă zece puncte din oficiu.<br/>"
        "• Timpul de lucru efectiv este de trei ore."
    )
    if not include_solutions:
        instr_p = Paragraph(instr_text, style_italic)
        t = Table([[instr_p]], colWidths=[A4[0] - 2 * 42.5])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
    exercises = exam_data["exercises"]
    printable_w = A4[0] - 2 * 42.5
    
    def make_subject_divider():
        t_div = Table([[""]], colWidths=[printable_w])
        t_div.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        return t_div

    if not include_solutions:
        # --- EXAM CONTENT ---
        # SUBIECTUL I
        story.append(Paragraph("<b>SUBIECTUL I (30 de puncte)</b>", style_section_title))
        for i in range(6):
            ex = exercises[i]
            cleaned_text = clean_latex_for_pdf(ex["text"])
            
            # Form exercise table layout (points, number, description)
            p_pts = Paragraph("5p", style_normal)
            p_num = Paragraph(f"<b>{i+1}.</b>", style_bold)
            p_desc = Paragraph(cleaned_text, style_normal)
            
            t = Table([[p_pts, p_num, p_desc]], colWidths=[30, 20, printable_w - 50])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(t)
            
        story.append(Spacer(1, 10))
        story.append(make_subject_divider())
        
        # SUBIECTUL al II-lea
        story.append(Paragraph("<b>SUBIECTUL al II-lea (30 de puncte)</b>", style_section_title))
        for i in range(6, 8):
            ex = exercises[i]
            ex_num = 1 if i == 6 else 2
            cleaned_text = clean_latex_for_pdf(ex["text"])
            
            # Format text cleanly by parts
            parts = [p.strip() for p in cleaned_text.split('\n\n') if p.strip()]
            intro_text = parts[0]
            
            p_num = Paragraph(f"<b>{ex_num}.</b>", style_bold)
            p_intro = Paragraph(intro_text, style_normal)
            
            t_intro = Table([["", p_num, p_intro]], colWidths=[30, 20, printable_w - 50])
            t_intro.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(t_intro)
            
            for part in parts[1:]:
                if part.startswith(('a)', 'b)', 'c)')):
                    prefix = part[:2]
                    sub_text = part[2:].strip()
                else:
                    prefix = ""
                    sub_text = part
                    
                p_pts = Paragraph("5p", style_normal)
                p_prefix = Paragraph(f"<b>{prefix}</b>", style_bold)
                p_sub = Paragraph(sub_text, style_normal)
                
                t_part = Table([[p_pts, p_prefix, p_sub]], colWidths=[30, 20, printable_w - 50])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('TOPPADDING', (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ]))
                story.append(t_part)
                
            story.append(Spacer(1, 8))
            
        story.append(Spacer(1, 10))
        story.append(make_subject_divider())
        
        # SUBIECTUL al III-lea
        story.append(Paragraph("<b>SUBIECTUL al III-lea (30 de puncte)</b>", style_section_title))
        for i in range(8, 10):
            ex = exercises[i]
            ex_num = 1 if i == 8 else 2
            cleaned_text = clean_latex_for_pdf(ex["text"])
            
            parts = [p.strip() for p in cleaned_text.split('\n\n') if p.strip()]
            intro_text = parts[0]
            
            p_num = Paragraph(f"<b>{ex_num}.</b>", style_bold)
            p_intro = Paragraph(intro_text, style_normal)
            
            t_intro = Table([["", p_num, p_intro]], colWidths=[30, 20, printable_w - 50])
            t_intro.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(t_intro)
            
            for part in parts[1:]:
                if part.startswith(('a)', 'b)', 'c)')):
                    prefix = part[:2]
                    sub_text = part[2:].strip()
                else:
                    prefix = ""
                    sub_text = part
                    
                p_pts = Paragraph("5p", style_normal)
                p_prefix = Paragraph(f"<b>{prefix}</b>", style_bold)
                p_sub = Paragraph(sub_text, style_normal)
                
                t_part = Table([[p_pts, p_prefix, p_sub]], colWidths=[30, 20, printable_w - 50])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('TOPPADDING', (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ]))
                story.append(t_part)
                
            story.append(Spacer(1, 8))
            
    else:
        # --- SOLUTIONS CONTENT (BAREM) ---
        story.append(Paragraph("<b>SUBIECTUL I</b>", style_section_title))
        for i in range(6):
            ex = exercises[i]
            cleaned_sol = clean_latex_for_pdf(ex["solution"])
            
            p_num = Paragraph(f"<b>{i+1}.</b>", style_bold)
            p_sol = Paragraph(cleaned_sol.replace('\n', '<br/>'), style_normal)
            
            t = Table([[p_num, p_sol]], colWidths=[30, printable_w - 30])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(KeepTogether(t))
            
        story.append(Spacer(1, 10))
        story.append(make_subject_divider())
        
        story.append(Paragraph("<b>SUBIECTUL al II-lea</b>", style_section_title))
        for i in range(6, 8):
            ex = exercises[i]
            ex_num = 1 if i == 6 else 2
            cleaned_sol = clean_latex_for_pdf(ex["solution"])
            
            story.append(Paragraph(f"<b>Exercițiul {ex_num}</b>", style_bold))
            story.append(Spacer(1, 4))
            
            parts = [p.strip() for p in cleaned_sol.split('\n\n') if p.strip()]
            for part in parts:
                p_part = Paragraph(part.replace('\n', '<br/>'), style_normal)
                t_part = Table([["", p_part]], colWidths=[20, printable_w - 20])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(KeepTogether(t_part))
                
            story.append(Spacer(1, 8))
            
        story.append(Spacer(1, 10))
        story.append(make_subject_divider())
        
        story.append(Paragraph("<b>SUBIECTUL al III-lea</b>", style_section_title))
        for i in range(8, 10):
            ex = exercises[i]
            ex_num = 1 if i == 8 else 2
            cleaned_sol = clean_latex_for_pdf(ex["solution"])
            
            story.append(Paragraph(f"<b>Exercițiul {ex_num}</b>", style_bold))
            story.append(Spacer(1, 4))
            
            parts = [p.strip() for p in cleaned_sol.split('\n\n') if p.strip()]
            for part in parts:
                p_part = Paragraph(part.replace('\n', '<br/>'), style_normal)
                t_part = Table([["", p_part]], colWidths=[20, printable_w - 20])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(KeepTogether(t_part))
                
            story.append(Spacer(1, 8))
            
    doc.build(story, canvasmaker=make_numbered_canvas(bac))
