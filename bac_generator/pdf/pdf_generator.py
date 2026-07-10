import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Try to register LiberationSerif font to support Romanian diacritics and match official Times New Roman style
FONT_NAME = "Helvetica"
BOLD_FONT_NAME = "Helvetica-Bold"
ITALIC_FONT_NAME = "Helvetica-Oblique"

current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "..", "..", "static", "fonts")
local_fonts = {
    "LiberationSerif": os.path.join(static_dir, "LiberationSerif-Regular.ttf"),
    "LiberationSerif-Bold": os.path.join(static_dir, "LiberationSerif-Bold.ttf"),
    "LiberationSerif-Italic": os.path.join(static_dir, "LiberationSerif-Italic.ttf")
}

fonts_registered = False
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
    Escapes <, >, and & in text for ReportLab Paragraph, except for valid HTML formatting tags:
    <b>, </b>, <i>, </i>, <br/>, <br>, <sup>, </sup>, <sub>, </sub>
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
    
    return text

def clean_latex_for_pdf(text: str) -> str:
    """
    Converts LaTeX formulas into clean, readable text/unicode/HTML representation for ReportLab.
    """
    if not text:
        return ""
        
    # Clean text environment
    text = re.sub(r'\\text\s*\{([^}]*)\}', r'\1', text)
    
    # Strip \left and \right
    text = text.replace(r"\left", "")
    text = text.replace(r"\right", "")
    
    # Strip literal braces
    text = text.replace(r"\{", "{")
    text = text.replace(r"\}", "}")
        
    # Replace common LaTeX structures with text/Unicode
    text = text.replace(r"\mathbb{R}", "R")
    text = text.replace(r"\mathbb{N}", "N")
    text = text.replace(r"\mathbb{Z}", "Z")
    text = text.replace(r"\mathbb{Q}", "Q")
    text = text.replace(r"\mathbb{C}", "C")
    text = text.replace(r"\iff", " <=> ")
    text = text.replace(r"\Leftrightarrow", " <=> ")
    text = text.replace(r"\Rightarrow", " => ")
    text = text.replace(r"\to", " -> ")
    text = text.replace(r"\rightarrow", " -> ")
    text = text.replace(r"\infty", "infinit")
    text = text.replace(r"\det", "det")
    
    # Greek letters
    text = text.replace(r"\lambda", "λ")
    text = text.replace(r"\Delta", "Δ")
    text = text.replace(r"\alpha", "α")
    text = text.replace(r"\beta", "β")
    text = text.replace(r"\pi", "π")
    text = text.replace(r"\theta", "θ")
    
    text = text.replace(r"\geq", " >= ")
    text = text.replace(r"\leq", " <= ")
    text = text.replace(r"\ge", " >= ")
    text = text.replace(r"\le", " <= ")
    text = text.replace(r"\neq", " != ")
    text = text.replace(r"\pm", " +/- ")
    text = text.replace(r"\dots", "...")
    text = text.replace(r"\cdot", "·")
    text = text.replace(r"\times", "×")
    text = text.replace(r"\setminus", " \ ")
    text = text.replace(r"\cap", " ∩ ")
    text = text.replace(r"\cup", " ∪ ")
    
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
    text = text.replace(r"\in", " in ")
    text = text.replace(r"^\circ", "°")
    text = text.replace(r"\_", "_")
    text = text.replace(r"\,", " ")
    
    # Recursively clean nested fractions: \frac{a}{b} -> (a)/(b)
    for _ in range(5):
        if r"\frac" not in text:
            break
        text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1)/(\2)', text)
        
    # Recursively clean roots: \sqrt[n]{x} -> n√(x), \sqrt{x} -> √(x)
    for _ in range(5):
        if r"\sqrt" not in text:
            break
        text = re.sub(r'\\sqrt\[([^\]]*)\]\{([^}]*)\}', r'\1√(\2)', text)
        text = re.sub(r'\\sqrt\{([^}]*)\}', r'√(\1)', text)
        
    # Binomial / Combinations: \binom{n}{k} -> C(n, k)
    text = re.sub(r'\\binom\{([^}]*)\}\{([^}]*)\}', r'C(\1, \2)', text)

    # Matrix environment: \begin{pmatrix} a & b \\ c & d \end{pmatrix}
    def format_matrix(match):
        matrix_body = match.group(1)
        rows = [r.strip() for r in matrix_body.split(r'\\') if r.strip()]
        formatted_rows = []
        for r in rows:
            cols = [c.strip() for c in r.split('&')]
            formatted_rows.append("[" + "  ".join(cols) + "]")
        return "\n" + "\n".join(formatted_rows) + "\n"
        
    text = re.sub(r'\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}', format_matrix, text, flags=re.DOTALL)
    
    # Determinant environment: \begin{vmatrix} a & b \\ c & d \end{vmatrix}
    def format_vmatrix(match):
        matrix_body = match.group(1)
        rows = [r.strip() for r in matrix_body.split(r'\\') if r.strip()]
        formatted_rows = []
        for r in rows:
            cols = [c.strip() for c in r.split('&')]
            formatted_rows.append("|" + "  ".join(cols) + "|")
        return "\n" + "\n".join(formatted_rows) + "\n"
        
    text = re.sub(r'\\begin\{vmatrix\}(.*?)\\end\{vmatrix\}', format_vmatrix, text, flags=re.DOTALL)
    
    # Cases environment: \begin{cases} ... \end{cases}
    def format_cases(match):
        cases_body = match.group(1)
        rows = [r.strip() for r in cases_body.split(r'\\') if r.strip()]
        formatted_rows = []
        for r in rows:
            cols = [c.strip() for c in r.split('&')]
            formatted_rows.append("{" + " dacă ".join(cols))
        return "\n" + "\n".join(formatted_rows) + "\n"
        
    text = re.sub(r'\\begin\{cases\}(.*?)\\end\{cases\}', format_cases, text, flags=re.DOTALL)
    
    # Clean up double "dacă dacă"
    text = re.sub(r'\bdacă\s+dacă\b', 'dacă', text)
    text = re.sub(r'\bdaca\s+daca\b', 'daca', text)

    # Superscripts and subscripts inside ReportLab Paragraph style (HTML tags)
    # Braced: ^{abc} -> <sup>abc</sup>
    text = re.sub(r'\^\{([^}]*)\}', r'<sup>\1</sup>', text)
    # Braced: _{abc} -> <sub>abc</sub>
    text = re.sub(r'\_\{([^}]*)\}', r'<sub>\1</sub>', text)
    # Single character: ^2 -> <sup>2</sup>, ^x -> <sup>x</sup>
    text = re.sub(r'\^([a-zA-Z0-9+-])', r'<sup>\1</sup>', text)
    # Single character: _1 -> <sub>1</sub>, _n -> <sub>n</sub>
    text = re.sub(r'\_([a-zA-Z0-9])', r'<sub>\1</sub>', text)

    # Remove inline math dollar signs ($) and display math ($$)
    text = text.replace("$$", "\n")
    text = text.replace("$", "")
    
    # Strip diacritics if fonts aren't registered
    if not fonts_registered:
        text = strip_diacritics(text)
        
    # Escape XML/HTML special characters to prevent ReportLab Paragraph parser crashes
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
        self.drawString(56.7, 30, f"Probă scrisă la matematică {spec_info['title']}")
        
        # Draw a thin horizontal rule above the footer
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.5)
        self.line(56.7, 45, A4[0] - 56.7, 45)
        
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
        rightMargin=56.7,
        leftMargin=56.7,
        topMargin=56.7,
        bottomMargin=56.7
    )
    
    styles = getSampleStyleSheet()
    
    # Custom typography (using LiberationSerif if registered)
    style_normal = ParagraphStyle(
        'BacNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
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
        fontSize=11,
        leading=15,
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
    divider = Table([[""]], colWidths=[A4[0] - 2 * 56.7])
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
        t = Table([[instr_p]], colWidths=[A4[0] - 2 * 56.7])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
    exercises = exam_data["exercises"]
    printable_w = A4[0] - 2 * 56.7
    
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
            
            # Form exercise table layout (number, description, points)
            p_num = Paragraph(f"<b>{i+1}.</b>", style_bold)
            p_desc = Paragraph(cleaned_text, style_normal)
            p_pts = Paragraph("<b>(5p)</b>", style_bold)
            
            t = Table([[p_num, p_desc, p_pts]], colWidths=[30, printable_w - 80, 50])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t)
            
        story.append(Spacer(1, 10))
        story.append(make_subject_divider())
        
        # SUBIECTUL II
        story.append(Paragraph("<b>SUBIECTUL al II-lea (30 de puncte)</b>", style_section_title))
        for i in range(6, 8):
            ex = exercises[i]
            ex_num = 1 if i == 6 else 2
            cleaned_text = clean_latex_for_pdf(ex["text"])
            
            # Format text cleanly by parts
            parts = cleaned_text.split('\n\n')
            intro_text = parts[0]
            
            story.append(Paragraph(f"<b>{ex_num}.</b> {intro_text}", style_normal))
            story.append(Spacer(1, 4))
            
            for part in parts[1:]:
                # Part should look like "a) ... (5p)"
                p_part = Paragraph(part, style_normal)
                t_part = Table([["", p_part]], colWidths=[20, printable_w - 20])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(t_part)
                
            story.append(Spacer(1, 8))
            
        story.append(Spacer(1, 10))
        story.append(make_subject_divider())
        
        # SUBIECTUL III
        story.append(Paragraph("<b>SUBIECTUL al III-lea (30 de puncte)</b>", style_section_title))
        for i in range(8, 10):
            ex = exercises[i]
            ex_num = 1 if i == 8 else 2
            cleaned_text = clean_latex_for_pdf(ex["text"])
            
            parts = cleaned_text.split('\n\n')
            intro_text = parts[0]
            
            story.append(Paragraph(f"<b>{ex_num}.</b> {intro_text}", style_normal))
            story.append(Spacer(1, 4))
            
            for part in parts[1:]:
                p_part = Paragraph(part, style_normal)
                t_part = Table([["", p_part]], colWidths=[20, printable_w - 20])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
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
            
            parts = cleaned_sol.split('\n\n')
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
            
            parts = cleaned_sol.split('\n\n')
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
