import json
import os
import re
from io import BytesIO
from functools import lru_cache
from flask import Blueprint, request, redirect, render_template, session, send_file, current_app, jsonify
from bac_generator import structure
from bac_generator import practice
from bac_generator.generators import difficulty as difficulty_mod
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
        {"value": "Radicali",             "i18n": "m_radicals"},
        {"value": "Puteri",               "i18n": "m_powers"},
        {"value": "Progresii",            "i18n": "m_progressions"},
        {"value": "Probabilități",        "i18n": "m_probability"},
        # Added once the corpus showed these fill real Subiect I slots that the
        # picker never offered: Procente is 44-49% of item 4 in M3/M_pedagogic,
        # Geometrie analitică is 80-100% of item 5 in every profile, and
        # Geometrie plană is roughly half of item 6.
        {"value": "Procente",             "i18n": "m_percentages"},
        {"value": "Geometrie analitică",  "i18n": "m_analytic_geometry"},
        {"value": "Geometrie plană",      "i18n": "m_plane_geometry"},
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

    profile = structure.resolve_profile(raw.get("profile"))
    level = difficulty_mod.normalize_level(raw.get("difficulty"))

    return {
        "selected": selected,
        "accent": accent,
        "omitted": omitted,
        "profile": profile,
        "profile_label": structure.profile_spec(profile)["label"],
        "difficulty": level,
        # The picker needs the slot map to tell the teacher, as they omit
        # things, when an omission can no longer be honoured.
        # Which lessons each slot can serve, so the picker can warn about an
        # omission it will not be able to honour. Profile-dependent now.
        "slot_lessons": [structure.slot_lessons(profile, slot)
                         for slot in structure.slots_for(profile)],
    }


def save_mode5_lesson_state(conversation_id, selected, accent, omitted,
                            profile=None, difficulty=None):
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

    state = {
        "selected": selected,
        "accent": accent,
        "omitted": omitted,
        # There is no migration tooling (init_db is a bare create_all), so the
        # picker's own session store is where new per-conversation settings go.
        "profile": structure.resolve_profile(profile),
        "difficulty": difficulty_mod.normalize_level(difficulty),
    }

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
    previous = mode5_lesson_state(conversation_id)
    state = save_mode5_lesson_state(
        conversation_id,
        request.form.getlist("lessons"),
        (request.form.get("accent") or "").strip() or None,
        request.form.getlist("omitted"),
        profile=request.form.get("profile") or previous["profile"],
        difficulty=request.form.get("difficulty") or previous["difficulty"],
    )
    action_type = request.form.get("action_type", "normal").strip()
    prompt = request.form.get("prompt", "").strip()

    # Generate the exam
    generator = BACExamGenerator()
    exam_data = generator.generate_exam(
        state["selected"],
        accent=state["accent"],
        omitted_lessons=state["omitted"],
        profile=state["profile"],
        difficulty=state["difficulty"],
    )

    db = SessionLocal

    # The profile a variant was built for has to travel with it: re-downloading
    # an old exam must use the letterhead it was generated under, not whatever
    # the conversation was switched to afterwards.
    conversation = db.get(Conversation, conversation_id)
    if conversation is not None and conversation.bac != state["profile"]:
        conversation.bac = state["profile"]

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
    db.add(Message(conversation_id=conversation_id, role="assistant",
                   content=content_html, exam_data=exam_json,
                   bac=state["profile"]))

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

    # Message.bac records the profile this exam was generated for; the
    # conversation's current setting is only a fallback for older rows.
    bac_profile = structure.DEFAULT_PROFILE
    if message:
        if getattr(message, "bac", None):
            bac_profile = message.bac
        else:
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


# ─────────────────────────── official paper archive ───────────────────────────

ARCHIVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "archive_index.json")
CORPUS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@lru_cache(maxsize=1)
def _archive():
    """The official papers, indexed by id.

    Serving the originals is the one place the corpus can be shown to a teacher
    verbatim: the PDFs themselves are perfect, it is only *text extraction*
    that loses square roots, so a generated exercise may never quote them but
    a printed paper may be handed over as-is.
    """
    try:
        with open(ARCHIVE_PATH, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {}
    return {paper["id"]: paper for paper in payload.get("papers", [])}


@bac_generator_bp.route("/bac-archive")
def bac_archive():
    if session.get("user_id") is None:
        return redirect("/login")

    papers = list(_archive().values())
    profile = (request.args.get("profile") or "").strip()
    year = (request.args.get("year") or "").strip()

    if profile in structure.PROFILES:
        papers = [p for p in papers if p["profile"] == profile]
    if year.isdigit():
        papers = [p for p in papers if p["year"] == int(year)]

    papers.sort(key=lambda p: (-(p["year"] or 0), p["profile"], p["filename"]))

    return render_template(
        "bac_archive.html",
        papers=papers,
        profiles=[(code, spec["label"]) for code, spec in structure.PROFILES.items()],
        years=sorted({p["year"] for p in _archive().values() if p["year"]}, reverse=True),
        active_profile=profile,
        active_year=year,
        total=len(_archive()),
    )


@bac_generator_bp.route("/bac-archive/<paper_id>")
def bac_archive_download(paper_id):
    if session.get("user_id") is None:
        return redirect("/login")

    # The path comes from the index, never from the request - `paper_id` is
    # only ever used as a dictionary key, so a traversal attempt simply misses.
    paper = _archive().get(paper_id)
    if not paper:
        return "Subiect inexistent.", 404

    full_path = os.path.normpath(os.path.join(CORPUS_ROOT, paper["path"]))
    if not full_path.startswith(CORPUS_ROOT) or not os.path.exists(full_path):
        return "Fișierul nu mai este disponibil.", 404

    return send_file(full_path, mimetype="application/pdf",
                     as_attachment=False, download_name=paper["filename"])


# =========================================================
# PRACTICE — standalone exercise generator
# =========================================================

@bac_generator_bp.route("/practice")
def practice_page():
    """The configuration form. The set itself is fetched, so a teacher can
    change one chapter and regenerate without losing the page."""
    return render_template(
        "practice.html",
        profiles=practice.PROFILES,
        levels=practice.LEVELS,
        chapters=practice.chapters_for(
            practice.structure.DEFAULT_PROFILE, difficulty_mod.DEFAULT_LEVEL
        ),
        default_profile=practice.structure.DEFAULT_PROFILE,
        default_level=difficulty_mod.DEFAULT_LEVEL,
        default_count=practice.DEFAULT_COUNT,
        min_count=practice.MIN_COUNT,
        max_count=practice.MAX_COUNT,
    )


@bac_generator_bp.route("/practice/chapters")
def practice_chapters():
    """Which chapters this profile/level can actually fill, so the form can
    grey out the rest instead of returning an empty set."""
    return jsonify(
        ok=True,
        chapters=practice.chapters_for(
            request.args.get("profile"), request.args.get("difficulty")
        ),
    )


@bac_generator_bp.route("/practice/generate", methods=["POST"])
def practice_generate():
    payload = request.get_json(silent=True) or {}
    result = practice.generate(
        profile=payload.get("profile"),
        chapters=payload.get("chapters") or [],
        level=payload.get("difficulty"),
        count=payload.get("count", practice.DEFAULT_COUNT),
        seed=payload.get("seed"),
    )
    if not result["exercises"]:
        return jsonify(
            ok=False,
            error="Nicio combinație de capitole și dificultate nu a produs exerciții. "
                  "Încearcă alt nivel sau mai multe capitole.",
        ), 422
    return jsonify(ok=True, **result)


@bac_generator_bp.route("/practice/export", methods=["POST"])
def practice_export():
    """Export the ticked exercises as a worksheet, through the same PDF/DOCX
    pipeline the chat modes use."""
    from secondary import exports

    payload = request.get_json(silent=True) or {}
    exercises = payload.get("exercises") or []
    if not exercises:
        return jsonify(ok=False, error="Nu ai selectat niciun exercițiu."), 400

    fmt = (payload.get("format") or "pdf").lower()
    with_solutions = bool(payload.get("include_solutions"))
    title = (payload.get("title") or "Fișă de exerciții").strip()

    content = practice.export_content(exercises, include_solutions=with_solutions)
    messages = [{"role": "assistant", "content": content}]
    meta = {"numbering": True, "sections": False, "sheet_type": payload.get("sheet_type") or ""}

    if fmt == "docx":
        blob = exports.build_messages_docx(title, messages, meta)
        mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        blob = exports.build_messages_pdf(title, messages, meta)
        mimetype = "application/pdf"
        ext = "pdf"

    safe = re.sub(r"[^\w.-]+", "_", title).strip("_") or "fisa"
    return send_file(
        BytesIO(blob),
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"{safe}.{ext}",
    )
