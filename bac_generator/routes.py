import json
import os
from flask import Blueprint, request, redirect, render_template, session, send_file, current_app, jsonify
from bac_generator.generator import BACExamGenerator
from bac_generator.pdf.pdf_generator import build_pdf
from models import SessionLocal, Conversation, Message

bac_generator_bp = Blueprint("bac_generator", __name__)

@bac_generator_bp.route("/generate-bac/<int:conversation_id>", methods=["POST"])
def generate_bac(conversation_id):
    """
    POST route to generate a new BAC exam.
    """
    if session.get("user_id") is None:
        return redirect("/login")

    # Get selected lessons from the checkbox form
    selected_lessons = request.form.getlist("lessons")
    action_type = request.form.get("action_type", "normal").strip()
    prompt = request.form.get("prompt", "").strip()

    # Generate the exam
    generator = BACExamGenerator()
    exam_data = generator.generate_exam(selected_lessons)

    db = SessionLocal

    # The quick-action buttons ("Rezolvare test", "Generează similare",
    # "Generează rand 2") build a long free-text prompt describing intent,
    # but this generator is a symbolic exam builder with no NLP input — it
    # never reads `prompt`, it just draws a fresh exam from the checked
    # lessons, same as the plain "Generează alt BAC" button. Saving that
    # long prompt verbatim as a "user" chat bubble misleadingly implies
    # the AI read and acted on it, so record a short honest label instead.
    ACTION_LABELS = {
        "solve_bac": "Rezolvare variantă BAC anterioară",
        "generate_similar_bac": "Generare variantă BAC similară",
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
