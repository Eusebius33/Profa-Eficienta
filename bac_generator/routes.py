import json
import os
from flask import Blueprint, request, redirect, render_template, session, send_file, current_app, jsonify
from bac_generator.generator import SLOT_LESSONS, BACExamGenerator
from bac_generator.pdf.pdf_generator import build_pdf
from models import SessionLocal, Conversation, Message

bac_generator_bp = Blueprint("bac_generator", __name__)


# The lesson catalogue the mode5 picker offers, grouped by school year. The
# `value` of each lesson has to match the `lesson` field the exercise
# generators tag their output with — see SLOT_LESSONS in generator.py — because
# that is what the accent/omit filtering compares against.
LESSON_GROUPS = [
    {"i18n": "grade_9", "label": "Clasa a IX-a", "lessons": [
        {"value": "Radicali",           "i18n": "m_radicals"},
        {"value": "Puteri",             "i18n": "m_powers"},
        {"value": "Progresii",          "i18n": "m_progressions"},
        {"value": "Probabilități",      "i18n": "m_probability"},
    ]},
    {"i18n": "grade_10", "label": "Clasa a X-a", "lessons": [
        {"value": "Funcții",            "i18n": "m_functions"},
        {"value": "Logaritmi",          "i18n": "m_logarithms"},
        {"value": "Numere complexe",    "i18n": "m_complex"},
        {"value": "Trigonometrie",      "i18n": "m_trig"},
    ]},
    {"i18n": "grade_11", "label": "Clasa a XI-a", "lessons": [
        {"value": "Matrici",            "i18n": "m_matrices"},
        {"value": "Legi de compoziție", "i18n": "m_composition"},
        {"value": "Limite",             "i18n": "m_limits"},
        {"value": "Derivate",           "i18n": "m_deriv"},
    ]},
    {"i18n": "grade_12", "label": "Clasa a XII-a", "lessons": [
        {"value": "Integrale definite", "i18n": "m_integrals"},
        {"value": "Polinoame",          "i18n": "m_polynomials"},
    ]},
]

ALL_LESSONS = [lesson["value"] for group in LESSON_GROUPS for lesson in group["lessons"]]

MODE5_STATE_KEY = "mode5_lessons"


def mode5_lesson_state(conversation_id):
    """Read back the lesson picker state (included / accent / omitted) for one
    mode5 conversation.

    This lives in the (server-side) Flask session rather than on the
    conversation row so it needs no schema migration. It is read on every
    render and on every generation, which is what makes a change in the picker
    carry over to the next prompt instead of resetting to the defaults.

    Defaults to every lesson included, no accent, nothing omitted.
    """
    store = session.get(MODE5_STATE_KEY) or {}
    raw = store.get(str(conversation_id)) or {}

    omitted = [l for l in raw.get("omitted", []) if l in ALL_LESSONS]
    selected = [
        l for l in raw.get("selected", ALL_LESSONS)
        if l in ALL_LESSONS and l not in omitted
    ]

    accent = raw.get("accent")
    if accent not in selected:
        accent = None

    return {
        "selected": selected,
        "accent": accent,
        "omitted": omitted,
        # The picker needs the slot map to tell the teacher, as they omit
        # things, when an omission can no longer be honoured.
        "slot_lessons": [list(lessons) for lessons in SLOT_LESSONS.values()],
    }


def save_mode5_lesson_state(conversation_id, selected, accent, omitted):
    """Normalise and persist the picker state, returning what was stored.

    Omitting a lesson outranks including it, and an accent only survives while
    it is still an included lesson — so the three lists can never contradict
    each other by the time the generator sees them.
    """
    omitted = [l for l in dict.fromkeys(omitted or []) if l in ALL_LESSONS]
    selected = [
        l for l in dict.fromkeys(selected or [])
        if l in ALL_LESSONS and l not in omitted
    ]
    accent = accent if accent in selected else None

    state = {"selected": selected, "accent": accent, "omitted": omitted}

    store = dict(session.get(MODE5_STATE_KEY) or {})
    store[str(conversation_id)] = state
    session[MODE5_STATE_KEY] = store

    return state


@bac_generator_bp.route("/generate-bac/<int:conversation_id>", methods=["POST"])
def generate_bac(conversation_id):
    """
    POST route to generate a new BAC exam.
    """
    if session.get("user_id") is None:
        return redirect("/login")

    # The picker posts its whole state, so whatever the teacher changed before
    # hitting generate is both what this exam is built from and what the next
    # prompt in this conversation starts out with.
    state = save_mode5_lesson_state(
        conversation_id,
        request.form.getlist("lessons"),
        (request.form.get("accent") or "").strip() or None,
        request.form.getlist("omitted"),
    )
    action_type = request.form.get("action_type", "normal").strip()
    prompt = request.form.get("prompt", "").strip()

    # Generate the exam
    generator = BACExamGenerator()
    exam_data = generator.generate_exam(
        state["selected"],
        accent=state["accent"],
        omitted_lessons=state["omitted"],
    )

    db = SessionLocal

    # The "Generează rand 2" quick action builds a long free-text prompt
    # describing intent, but this generator is a symbolic exam builder with no
    # NLP input — it never reads `prompt`, it just draws a fresh exam from the
    # picker state, same as the plain "Generează alt BAC" button. Saving that
    # long prompt verbatim as a "user" chat bubble misleadingly implies the AI
    # read and acted on it, so record a short honest label instead.
    ACTION_LABELS = {
        "generate_row_2_bac": "Generare rândul 2",
    }
    display_message = ACTION_LABELS.get(action_type) or prompt or None

    if display_message:
        db.add(Message(conversation_id=conversation_id, role="user", content=display_message))

    # Format content to render in HTML
    content_html = exam_data["html_preview"]

    # Serialize exam data to JSON
    exam_json = json.dumps(exam_data)

    # Insert assistant message with exam_data JSON
    db.add(Message(conversation_id=conversation_id, role="assistant", content=content_html, exam_data=exam_json))

    db.commit()

    return redirect(f"/mode5/{conversation_id}")

@bac_generator_bp.route("/generate-bac/download/<int:message_id>")
def download_pdf(message_id):
    """
    Downloads the PDF for a specific generated BAC exam message.
    Query parameters:
    - type: "subject" (default) or "solution"
    """
    if session.get("user_id") is None:
        return redirect("/login")

    pdf_type = request.args.get("type", "subject")

    db = SessionLocal

    # Retrieve the message
    message = db.get(Message, message_id)

    bac_profile = "M3"
    if message:
        conversation = db.get(Conversation, message.conversation_id)
        if conversation and conversation.bac:
            bac_profile = conversation.bac

    if not message or not message.exam_data:
        return "Eroare: Examenele generate anterior nu au date matematice disponibile.", 404

    exam_data = json.loads(message.exam_data)
    
    # Create a temporary PDF file in the uploads/ directory
    os.makedirs("uploads", exist_ok=True)
    filename = f"bac_exam_{message_id}_{pdf_type}.pdf"
    filepath = os.path.join("uploads", filename)
    
    include_solutions = (pdf_type == "solution")
    
    # Build the PDF
    build_pdf(filepath, exam_data, include_solutions=include_solutions, bac=bac_profile)
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=f"Varianta_BAC_{'Rezolvare_' if include_solutions else ''}{message_id}.pdf",
        mimetype="application/pdf"
    )
