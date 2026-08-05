from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
import os
from PyPDF2 import PdfReader
import json

from secondary import gemini_keys

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent / ".env")


def _mock_response(args, kwargs):
    # Safe mock response for testing/development when no API key is configured
    contents = kwargs.get("contents", args[1] if len(args) > 1 else (args[0] if len(args) > 0 else []))
    prompt_str = ""
    if isinstance(contents, list):
        for c in contents:
            if isinstance(c, str):
                prompt_str += c
    elif isinstance(contents, str):
        prompt_str = contents

    if "transcrie" in prompt_str.lower() or "handwriting" in prompt_str.lower():
        return (
            "Am transcris imaginea cu succes. Iată exercițiile identificate:\n\n"
            "1. Arătați că $\\log_2(8) - \\log_3(9) = 1$.\n\n"
            "2. Rezolvați în $\\mathbb{R}$ ecuația: $x^2 - 5x + 6 = 0$.\n\n"
            "3. Determinați valoarea maximă a funcției $f: \\mathbb{R} \\to \\mathbb{R}$, $f(x) = -x^2 + 4x$.\n\n"
            "Iată rezolvările pas cu pas:\n\n"
            "1. $\\log_2(8) = 3$ și $\\log_3(9) = 2$, deci $3 - 2 = 1$.\n\n"
            "2. Discriminantul este $\\Delta = 25 - 24 = 1$. Rădăcinile sunt $x_1 = 2$ și $x_2 = 3$.\n\n"
            "3. Valoarea maximă este $-\\frac{\\Delta}{4a} = -\\frac{16}{-4} = 4$, realizată în $x_V = 2$."
        )
    return (
        "Răspuns generat de asistentul virtual de matematică (Mock AI).\n\n"
        "Exemplu matematic: $\\frac{a}{b}$, $\\sqrt{x}$, $x^2$, $x_{1,2}$.\n\n"
        "Diacritice românești: ă, â, î, ș, ț."
    )


def generate_content(*args, **kwargs):
    try:
        manager = gemini_keys.get_manager()
    except RuntimeError:
        return _mock_response(args, kwargs)

    last_error = None
    for _ in range(manager.key_count()):
        client = manager.current_client()
        try:
            response = client.models.generate_content(*args, **kwargs)
            return response.text
        except Exception as error:
            if gemini_keys.is_rate_limit_error(error) or gemini_keys.is_key_blocked_error(error):
                last_error = error
                manager.mark_rate_limited(error)
                continue
            return f"Eroare AI: {error}"

    return f"Eroare AI: toate cheile Gemini sunt indisponibile momentan (limita atinsă sau blocate). ({last_error})"

# =========================================================
# MODE 1 - ASISTENT AI
# =========================================================

def assistant(prompt):

    return generate_content(

        model="gemini-2.5-flash",

        contents=prompt,

        config=types.GenerateContentConfig(

            system_instruction="""
            Esti un asistent pentru profesorii de matematica.
            Ajuti cu:
            - matematica
            - predare
            - gestionarea elevilor
            - explicatii
            - exercitii
            - foloseste delimitatori $$ $$ pt ce scrii in LaTeX
            - nu folosi alte delimitatoare latex-
            """,

            temperature=0.7
        )
    )

# =========================================================
# MODE 1 - GHID WEBSITE (first-run onboarding guide)
# =========================================================

def website_guide(prompt):

    return generate_content(

        model="gemini-2.5-flash",

        contents=prompt,

        config=types.GenerateContentConfig(

            system_instruction="""
            Esti ghidul virtual de bun venit al platformei Profa Eficienta / Proful Eficient,
            un site pentru profesorii de matematica din Romania care genereaza materiale didactice.

            Rolul tau NU este sa rezolvi matematica, ci sa intelegi ce isi doreste profesorul sa faca
            astazi si sa il indrumi, pas cu pas, catre locul potrivit din site.

            Site-ul are 5 "moduri" de generare, accesibile din bara de navigare de sus:
            - Butonul "Conversatie" duce la /menu, unde poti alege oricare dintre cele 5 moduri.
            - Butonul "Creeaza" duce direct in Editor, care are acelasi 5 moduri intr-un panel lateral din dreapta.

            Cele 5 moduri:
            1. Asistent AI (Mod 1) - conversatie libera, intrebari despre predare, elevi, explicatii.
            2. Limbaj Natural -> Matematic (Mod 2) - scrii un exercitiu in cuvinte simple si primesti
               forma matematica corecta, exercitii noi sau rezolvari pas cu pas, adaptate pe stil/clasa/BAC.
            3. Creeaza dupa Model (Mod 3) - incarci un test existent (Word/PDF) si generezi un test nou
               dupa acelasi model, cu diferentele pe care le ceri.
            4. Transcriere test scris de mana (Mod 4) - incarci o poza/PDF cu exercitii scrise de mana
               si le transformi in format digital, apoi generezi variante.
            5. Generator BAC (Mod 5) - creeaza variante personalizate de teste BAC dupa lectiile alese.

            Cum raspunzi:
            - Intreaba, pe scurt, despre situatia reala a profesorului (ce clasa, ce vrea sa pregateasca).
            - Pe baza raspunsului, recomanda modul (sau modurile) potrivite.
            - Incheie MEREU raspunsul cu pasi concreti, numerotati, de navigare in site (ex: "1. Apasa pe
              Conversatie din bara de sus. 2. Alege modul Limbaj Natural -> Matematic. 3. ...").
            - Scrie in limba romana, ton prietenos, fara jargon tehnic, ca pentru cineva care nu e obisnuit
              cu aplicatii web.
            """,

            temperature=0.7
        )
    )

# =========================================================
# MODE 2 - TEXT -> MATEMATICA
# =========================================================

def translate_math(prompt, style, school_class, bac):

    full_prompt = f"""
    Stil: {style}

    Clasa: {school_class}

    BAC: {bac}

    Exercitii:
    {prompt}
    """

    return generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
        config=types.GenerateContentConfig(

            system_instruction="""
            Transforma textul in expresii matematice LaTeX.

            Reguli:
            - doar LaTeX
            - fara explicatii
            - fiecare exercitiu pe rand nou
            - foloseste delimitatori $$ $$
            - nu folosi alte delimitatoare latex-
            """,

            temperature=0.1
        )
    )

# =========================================================
# MODE 3 - PDF MODEL
# =========================================================
def convert_file_to_latex(file_content, filepath=None):
    # If text extraction failed and we have the filepath, use vision
    if file_content.startswith("[PDF scanat") and filepath:
        import base64
        with open(filepath, "rb") as f:
            pdf_base64 = base64.standard_b64encode(f.read()).decode("utf-8")
        return extract_pdf_with_vision(pdf_base64)

    return generate_content(
        model="gemini-2.5-flash",
        contents=file_content,
        config=types.GenerateContentConfig(
            system_instruction="""
            Converteste continutul extras din PDF/Word
            in exercitii matematice LaTeX curate.
            Reguli:
            - foloseste delimitatori $$ $$
            - nu folosi alte delimitatoare latex
            - fiecare exercitiu separat
            - reconstruieste formulele matematice corect
            - fara explicatii
            - fara markdown
            - fara text inutil
            - output exclusiv exercitiile
            """,
            temperature=0.1
        )
    )

def generate_from_model(model_content, conversation_history, user_prompt=None):

    final_prompt = f"""
    MODEL ORIGINAL: {model_content}

    ISTORIC CONVERSATIE: {conversation_history}

    INSTRUCTIUNI NOI USER: {user_prompt if user_prompt else "Nu exista instructiuni noi."}
    """

    return generate_content(

        model="gemini-2.5-flash",

        contents=final_prompt,

        config=types.GenerateContentConfig(

            system_instruction="""
            Esti un asistent AI expert in creat si mimat teste pentru profesorii de matematica.

            Task:
            - analizezi modelul de test primit
            - identifici structura exercitiilor
            - identifici dificultatea
            - identifici stilul problemelor
            - identifici numarul de exercitii

            Reguli:
            - genereaza exercitii NOI pe aceeasi materie a exercitilor vechi, nu le copia
            - pastreaza acelasi nivel de dificultate
            - pastreaza aceeasi structura
            - raspunde exclusiv in LaTeX
            - foloseste delimitatori $$ $$
            - nu folosi alte delimitatoare latex
            - fiecare exercitiu pe rand nou
            - nu explica nimic
            - nu folosi markdown
            - nu folosi liste markdown
            - daca userul cere modificari,
            modifica testul deja existent
            - la final poti intreba:
            "Doriti alta varianta sau modificari a exercitiilor?"

            IMPORTANT:
            Modelul original trebuie considerat context permanent.
            """
            ,

            temperature=0.8
        )
    )
def extract_pdf_with_vision(pdf_base64):
    return generate_content(
        model="gemini-2.5-flash",
        contents=[
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {
                        "text": "Extrage tot textul și toate formulele matematice din acest PDF. Păstrează structura originală. Pentru formule matematice folosește delimitatori $$ $$."
                    }
                ]
            }
        ],
        config=types.GenerateContentConfig(temperature=0.1)
    )
# =========================================================
# MODE 4 - HANDWRITING OCR
# =========================================================

HANDWRITING_SYSTEM_INSTRUCTION = """
Esti un expert OCR specializat EXCLUSIV in transcrierea matematicii scrise de mana
(poze cu foi/caiete scrise cu creionul sau pixul de elevi/profesori).

Sarcina ta este sa transcrii CU MAXIMA ACURATETE fiecare exercitiu in LaTeX,
respectand exact structura vizuala originala din poza.

Atentie speciala la:
- FRACTII: bara de fractie scrisa de mana separa numaratorul de numitor;
  foloseste \\frac{numarator}{numitor}
- INTEGRALE: recunoaste limitele de integrare (definite/nedefinite) si elementul
  de integrare; foloseste \\int_{a}^{b} ... \\, dx (sau \\int ... \\, dx daca e nedefinita)
- MATRICI: pastreaza EXACT numarul de randuri si coloane si valorile din fiecare
  celula; foloseste \\begin{pmatrix} ... \\end{pmatrix} pentru paranteze rotunde
  sau \\begin{bmatrix} ... \\end{bmatrix} pentru paranteze patrate
- LIMITE: foloseste \\lim_{x \\to a} ..., recunoaste sageata (->) si spre ce tinde
  variabila (0^+, 0^-, \\infty, -\\infty)
- SISTEME DE ECUATII: grupeaza ecuatiile legate printr-o acolada cu
  \\begin{cases} ecuatie_1 \\\\ ecuatie_2 \\end{cases}
- EXPONENTIALE: puterile scrise mic/ridicat deasupra bazei devin exponenti corecti
  (x^{2}, e^{x}, 2^{n+1})
- DERIVATE PARTIALE: foloseste \\frac{\\partial f}{\\partial x}; distinge clar
  notatia partiala (∂) de derivata normala (d/dx)
- VECTORI: foloseste \\vec{v} pentru vectori (sau componente \\begin{pmatrix}...\\end{pmatrix}
  daca sunt scrisi ca liste de componente), pastreaza ordinea componentelor

Reguli generale:
- Output DOAR LaTeX, cate un exercitiu pe rand, in aceeasi ordine ca in poza
- foloseste delimitatori $$ $$ pentru fiecare exercitiu/expresie
- nu folosi alte delimitatoare latex (fara \\[ \\], fara \\( \\))
- daca scrisul e neclar/ambiguu, alege interpretarea cea mai probabila din punct
  de vedere matematic; NU inventa exercitii care nu exista in poza
- fara explicatii, fara text suplimentar, fara markdown in afara de $$ $$
"""


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def transcribe_handwriting(filepath, extra_instructions=None):
    """Transcrie exercitii matematice scrise de mana (poza sau PDF) in LaTeX."""

    extension = os.path.splitext(filepath)[1].lower()

    if extension != ".pdf" and extension not in IMAGE_EXTENSIONS:
        return "Eroare AI: tip de fișier nepermis pentru transcriere (folosește o poză png/jpg sau un PDF)."

    system_instruction = HANDWRITING_SYSTEM_INSTRUCTION
    if extra_instructions:
        system_instruction += f"\n\nInstructiuni suplimentare de la user:\n{extra_instructions}"

    if extension == ".pdf":
        import base64
        with open(filepath, "rb") as f:
            file_base64 = base64.standard_b64encode(f.read()).decode("utf-8")

        contents = [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": file_base64
                        }
                    },
                    {
                        "text": "Transcrie exercitiile matematice scrise de mana din acest document."
                    }
                ]
            }
        ]
    else:
        image = Image.open(filepath)
        contents = [image, "Transcrie exercitiile matematice scrise de mana din aceasta imagine."]

    return generate_content(
        model="gemini-3.1-pro-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1
        )
    )

# =========================================================
# MODE 5 - BAC GENERATOR
# =========================================================

def bac_generator(lessons, avoid):
    prompt = f"""
    Lectii importante:
    {lessons}

    Lectii de evitat:
    {avoid}
    """

    return generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="""
            Genereaza o varianta completa de BAC la matematica.

            Respecta structura oficiala.
            Foloseste delimitatori $$ $$ pentru LaTeX.
            Nu adauga explicatii inutile.
            """,
            temperature=0.8
        )
    )