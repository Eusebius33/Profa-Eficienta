import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Try to register Arial font to support Romanian diacritics (ș, ț, ă, â, î)
FONT_NAME = "Helvetica"
BOLD_FONT_NAME = "Helvetica-Bold"
ITALIC_FONT_NAME = "Helvetica-Oblique"

# Check standard Windows font paths
windows_fonts = {
    "Arial": "C:\\Windows\\Fonts\\arial.ttf",
    "Arial-Bold": "C:\\Windows\\Fonts\\arialbd.ttf",
    "Arial-Italic": "C:\\Windows\\Fonts\\ariali.ttf"
}

fonts_registered = False
try:
    if os.path.exists(windows_fonts["Arial"]):
        pdfmetrics.registerFont(TTFont("Arial", windows_fonts["Arial"]))
        pdfmetrics.registerFont(TTFont("Arial-Bold", windows_fonts["Arial-Bold"]))
        pdfmetrics.registerFont(TTFont("Arial-Italic", windows_fonts["Arial-Italic"]))
        FONT_NAME = "Arial"
        BOLD_FONT_NAME = "Arial-Bold"
        ITALIC_FONT_NAME = "Arial-Italic"
        fonts_registered = True
except Exception:
    pass

def strip_diacritics(text: str) -> str:
    """
    Fallback cleaner: replaces Romanian diacritics with standard English counterparts
    to prevent encoding/rendering errors on systems without the registered Arial font.
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
    <b>, </b>, <i>, </i>, <br/>, <br>
    """
    if not text:
        return ""
        
    # Replace valid tags with placeholders
    text = text.replace("<b>", "__B_OPEN__")
    text = text.replace("</b>", "__B_CLOSE__")
    text = text.replace("<i>", "__I_OPEN__")
    text = text.replace("</i>", "__I_CLOSE__")
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
    text = text.replace("__BR__", "<br/>")
    
    return text

def clean_latex_for_pdf(text: str) -> str:
    """
    Converts LaTeX formulas into clean, readable text/unicode representation for ReportLab.
    """
    if not text:
        return ""
        
    # Clean text environment
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
        
    # Replace common LaTeX structures with text/Unicode
    text = text.replace(r"\mathbb{R}", "R")
    text = text.replace(r"\iff", " <=> ")
    text = text.replace(r"\Leftrightarrow", " <=> ")
    text = text.replace(r"\Rightarrow", " => ")
    text = text.replace(r"\to", " -> ")
    text = text.replace(r"\rightarrow", " -> ")
    text = text.replace(r"\infty", " infinit ")
    text = text.replace(r"\det", "det")
    text = text.replace(r"\lambda", "lambda")
    text = text.replace(r"\Delta", "Delta")
    text = text.replace(r"\geq", " >= ")
    text = text.replace(r"\leq", " <= ")
    text = text.replace(r"\neq", " != ")
    text = text.replace(r"\pm", " +/- ")
    text = text.replace(r"\dots", "...")
    text = text.replace(r"\cdot", " · ")
    text = text.replace(r"\times", " × ")
    text = text.replace(r"\hat{A}", "A")
    text = text.replace(r"\hat{B}", "B")
    text = text.replace(r"\hat{C}", "C")
    text = text.replace(r"\sin", "sin")
    text = text.replace(r"\cos", "cos")
    text = text.replace(r"\log", "log")
    text = text.replace(r"\ln", "ln")
    text = text.replace(r"\lim", "lim")
    text = text.replace(r"\iint", "∬")
    text = text.replace(r"\int", "∫")
    text = text.replace(r"\in", " in ")
    text = text.replace(r"^\circ", "°")
    text = text.replace(r"\_", "_")
    text = text.replace(r"\,", " ")
    
    # Strip exponent/subscript braces: ^{x} -> ^x, _{1} -> _1
    text = re.sub(r'\^\{([^}]*)\}', r'^\1', text)
    text = re.sub(r'\_\{([^}]*)\}', r'_\1', text)
    
    # Vector arrows: \vec{u} -> u, \vec{i} -> i
    text = re.sub(r'\\vec\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\vec\s+([a-zA-Z])', r'\1', text)
    
    # Fractions: \frac{a}{b} -> a/b
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1)/(\2)', text)
    
    # Square root: \sqrt{x} -> √x or \sqrt[n]{x}
    text = re.sub(r'\\sqrt\{([^}]*)\}', r'√(\1)', text)
    
    # Matrix environment: \begin{pmatrix} a & b \\ c & d \end{pmatrix}
    # Convert to a readable string format
    def format_matrix(match):
        matrix_body = match.group(1)
        rows = [r.strip() for r in matrix_body.split(r'\\')]
        formatted_rows = []
        for r in rows:
            cols = [c.strip() for c in r.split('&')]
            formatted_rows.append("[" + "  ".join(cols) + "]")
        return "\n" + "\n".join(formatted_rows) + "\n"
        
    text = re.sub(r'\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}', format_matrix, text, flags=re.DOTALL)
    
    # Cases environment: \begin{cases} ... \end{cases}
    def format_cases(match):
        cases_body = match.group(1)
        rows = [r.strip() for r in cases_body.split(r'\\')]
        formatted_rows = []
        for r in rows:
            cols = [c.strip() for c in r.split('&')]
            formatted_rows.append("  " + " dacă ".join(cols))
        return "\n" + "\n".join(formatted_rows) + "\n"
        
    text = re.sub(r'\\begin\{cases\}(.*?)\\end\{cases\}', format_cases, text, flags=re.DOTALL)
    
    # Remove inline math dollar signs ($) and display math ($$)
    text = text.replace("$$", "\n")
    text = text.replace("$", "")
    
    # Strip diacritics if fonts aren't registered
    if not fonts_registered:
        text = strip_diacritics(text)
        
    # Escape XML/HTML special characters to prevent ReportLab Paragraph parser crashes
    text = escape_xml_tags(text)
        
    return text

def build_pdf(filepath: str, exam_data: dict, include_solutions: bool = False):
    """
    Builds a professional PDF file for the generated BAC exam.
    """
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom typography
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
        fontName=style_normal.fontName,
        fontSize=10,
        leading=14,
        alignment=1
    )
    
    style_section_title = ParagraphStyle(
        'BacSectionTitle',
        parent=style_normal,
        fontName=BOLD_FONT_NAME,
        fontSize=11,
        leading=15,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#0F172A')
    )
    
    story = []
    
    # 1. Official Header
    story.append(Paragraph("<b>Ministerul Educației</b>", style_header_title))
    story.append(Paragraph("Centrul Național de Politici și Evaluare în Educație", style_header_subtitle))
    story.append(Spacer(1, 6))
    
    title_suffix = " - BAREM DE EVALUARE ȘI DE NOTARE" if include_solutions else ""
    story.append(Paragraph(f"<b>Examenul național de bacalaureat 2026</b>{title_suffix}", style_header_title))
    story.append(Paragraph("<b>Proba E. c)</b>", style_header_title))
    story.append(Paragraph("<b>Matematică M_tehnologic</b>", style_header_title))
    story.append(Spacer(1, 6))
    
    # Subtitle filiera
    story.append(Paragraph("<i>Filiera tehnologică: profilul servicii, resurse naturale și protecția mediului, profilul tehnic</i>", style_header_subtitle))
    story.append(Spacer(1, 10))
    
    # General instructions box
    instr_text = (
        "• Toate subiectele sunt obligatorii. Se acordă zece puncte din oficiu.<br/>"
        "• Timpul de lucru efectiv este de trei ore."
    )
    if not include_solutions:
        instr_p = Paragraph(instr_text, style_italic)
        t = Table([[instr_p]], colWidths=[510])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
    exercises = exam_data["exercises"]
    
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
            
            t = Table([[p_num, p_desc, p_pts]], colWidths=[30, 430, 50])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t)
            
        story.append(Spacer(1, 10))
        
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
                t_part = Table([["", p_part]], colWidths=[20, 490])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(t_part)
                
            story.append(Spacer(1, 8))
            
        story.append(Spacer(1, 10))
        
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
                t_part = Table([["", p_part]], colWidths=[20, 490])
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
            
            t = Table([[p_num, p_sol]], colWidths=[30, 480])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(KeepTogether(t))
            
        story.append(Spacer(1, 10))
        
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
                t_part = Table([["", p_part]], colWidths=[20, 490])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(KeepTogether(t_part))
                
            story.append(Spacer(1, 8))
            
        story.append(Spacer(1, 10))
        
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
                t_part = Table([["", p_part]], colWidths=[20, 490])
                t_part.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(KeepTogether(t_part))
                
            story.append(Spacer(1, 8))
            
    doc.build(story)
