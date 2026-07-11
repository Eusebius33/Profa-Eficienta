from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
import os
import sqlite3
from PyPDF2 import PdfReader
import json
# =========================================================
#Database
# =========================================================

connect = sqlite3.connect("profu.db", check_same_thread=False)

connect.row_factory = sqlite3.Row

db = connect.cursor()

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

api_key = os.getenv("GEMINI_API_KEY")

client = None


def get_client():
    global client

    if client is None:
        if not api_key:
            raise RuntimeError(
                "AI nu este configurat. Adauga GEMINI_API_KEY in fisierul .env."
            )

        client = genai.Client(api_key=api_key)

    return client


def generate_content(*args, **kwargs):
    try:
        response = get_client().models.generate_content(*args, **kwargs)
        return response.text
    except Exception as error:
        return f"Eroare AI: {error}"

# =========================================================
# MODE 1 - ASISTENT AI
# =========================================================

def assistant(prompt):

    return generate_content(

        model="gemini-flash-lite-latest",

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
        model="gemini-flash-lite-latest",
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
        model="gemini-flash-lite-latest",
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

        model="gemini-flash-lite-latest",

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
        model="gemini-flash-lite-latest",
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

def handwriting(prompt, differences):

    image = Image.open("static/userpic.png")

    return generate_content(

        model="gemini-flash-lite-latest",

        contents=[image, prompt],

        config=types.GenerateContentConfig(

            system_instruction=f"""
            Transcrie testul scris de mana.
            - foloseste delimitatori $$ $$ pt LaTeX
            - nu folosi alte delimitatoare latex-
            -tot ce tine de matematica folosesti LaTeX

            Diferente:
            {differences}

            Foloseste LaTeX.
            """,

            temperature=0.3
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
        model="gemini-flash-lite-latest",
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
