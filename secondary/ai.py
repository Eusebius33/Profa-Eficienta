from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
import os
from sentence_transformers import SentenceTransformer
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

def handwriting(prompt, differences):

    image = Image.open("static/userpic.png")

    return generate_content(

        model="gemini-2.5-flash",

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
# db.execute("""
# CREATE TABLE IF NOT EXISTS exam_chunks (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     conversation_id INTEGER,
#     source_file TEXT,
#     subject TEXT,
#     lesson TEXT,
#     difficulty TEXT,
#     content TEXT
# )
# """)
# db.execute("""
# CREATE VIRTUAL TABLE exam_chunks_vss USING vss0(
#     embedding(384)
# );
# """)
def split_exercises(content):
    exercises = []
    current = []
    lines = content.splitlines()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue
        # detect new exercise
        if stripped.startswith("$$") and current:
            exercises.append("\n".join(current))
            current = []

        current.append(stripped)

    if current:
        exercises.append("\n".join(current))

    return exercises

def ingest_bac_folder(folder_path):
    for filename in os.listdir(folder_path):

        if not filename.endswith(".pdf"):
            continue

        filepath = os.path.join(folder_path, filename)
        raw = file_read(filepath)
        latex = ai.convert_file_to_latex(raw)
        exercises = split_exercises(latex)

        for ex in exercises:
            vector = embedding_model.encode(ex)
            save_to_sqlite(ex, vector, filename)

def bac_generator(lessons, avoid):
    #pdf delivery & encoding
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = embedding_model.encode(exercise)

    db.execute(
    """
    INSERT INTO exam_chunks (conversation_id, source_file, content)
    VALUES (?, ?, ?)
    """,
    (conversation_id, filename, exercise)
    )
    chunk_id = db.lastrowid

    db.execute(
    """
    INSERT INTO exam_chunks_vss (rowid, embedding) VALUES (?, ?)
    """,(chunk_id, json.dumps(vector.tolist()))
    )
    #encode user input
    query_vector = embedding_model.encode(user_prompt)
    db.execute("""
    SELECT exam_chunks.content FROM exam_chunks_vss
    JOIN exam_chunks ON exam_chunks.id = exam_chunks_vss.rowid
    WHERE vss_search(embedding, ?) LIMIT 10;
    """)
    #AI Model
    prompt = f"""
    Lectii importante:
    {lessons}

    Lectii de omis:
    {avoid}
    """

    return generate_content(

        model="gemini-2.5-flash",

        contents=prompt,

        config=types.GenerateContentConfig(

            system_instruction="""
            Genereaza o varianta completa de BAC matematica.
            Respecta structura oficiala romana.
            -pt matematica folosesti LaTex
            Cand scrii matematica:
            - formule mari foloseste $$...$$
            - nu folosi alte delimitatoare latex-
            """,

            temperature=0.8
        )
    )
