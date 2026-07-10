from pathlib import Path
from PIL import Image
from google.genai import types
from secondary import ai
import base64


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSIONS = {".pdf"}


def extract_handwriting(filepath, user_prompt=""):
    """
    Extract handwritten math exercises from an uploaded image or PDF.
    Returns clean Romanian text + LaTeX using $$ $$ delimiters.
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    instruction = f"""
    Transcrie conținutul scris de mână din fișier.

    Cerințe:
    - Transformă exercițiile în text digital clar.
    - Reconstruiește formulele matematice cât mai corect.
    - Pentru matematică folosește delimitatori $$ $$.
    - Nu folosi alte delimitatoare LaTeX.
    - Păstrează numerotarea exercițiilor dacă există.
    - Dacă ceva este neclar, marchează cu [neclar].
    - Răspunde în română.
    - Nu inventa exerciții care nu apar în imagine.

    Instrucțiuni suplimentare de la utilizator:
    {user_prompt if user_prompt else "Nu există."}
    """

    if ext in IMAGE_EXTENSIONS:
        image = Image.open(filepath)

        return ai.generate_content(
            model="gemini-2.5-flash",
            contents=[image, instruction],
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )

    if ext in PDF_EXTENSIONS:
        with open(filepath, "rb") as f:
            pdf_base64 = base64.standard_b64encode(f.read()).decode("utf-8")

        return ai.generate_content(
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
                            "text": instruction
                        }
                    ]
                }
            ],
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )

    return "Tip de fișier neacceptat pentru OCR. Încarcă PNG, JPG, JPEG sau PDF."


def generate_from_transcription(transcription, user_prompt="", action_type="normal"):
    """
    Generate solution / row 2 / modified version based on the latest transcription.
    """

    full_prompt = f"""
    TRANSCRIERE EXISTENTĂ:
    {transcription}

    ACȚIUNE:
    {action_type}

    CERERE UTILIZATOR:
    {user_prompt if user_prompt else "Nu există cerere suplimentară."}
    """

    return ai.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction="""
            Ești un asistent AI pentru profesori de matematică.

            Dacă ACȚIUNE este solve_test:
            - rezolvă complet testul pas cu pas
            - include explicații clare
            - include răspunsurile finale

            Dacă ACȚIUNE este generate_row_2:
            - generează rândul 2 pentru test
            - păstrează aceeași structură și dificultate
            - schimbă exercițiile și valorile numerice

            Dacă ACȚIUNE este normal:
            - aplică cererea utilizatorului asupra transcrierii existente

            Reguli:
            - folosește delimitatori $$ $$ pentru LaTeX
            - nu folosi alte delimitatoare LaTeX
            - răspunde în română
            """,
            temperature=0.7
        )
    )
