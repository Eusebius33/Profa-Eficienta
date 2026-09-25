import markdown
import os
from flask import request, redirect, render_template, session
from sqlalchemy import select, func
from werkzeug.utils import secure_filename
from secondary import ai
from secondary import adjacent
from models import Conversation, Message


def _save_attachment(upload_folder, uploaded_file, allowed_file):
    """Persist a file attached to a mid-conversation message.

    Returns (filepath, filename, error). All three are None/None/None when no
    file was sent at all; `error` carries a message to show the teacher when
    one was sent but could not be used, so a rejected upload is never dropped
    in silence. Uploads share one flat folder, so a name that is already taken
    gets a numbered suffix rather than overwriting another teacher's model.
    """
    if not uploaded_file or not uploaded_file.filename:
        return None, None, None

    if not allowed_file(uploaded_file.filename):
        return None, None, "Tip de fișier nepermis"

    filename = secure_filename(uploaded_file.filename)
    if not filename:
        return None, None, "Nume de fișier invalid"

    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)

    stem, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{stem}_{counter}{ext}"
        counter += 1

    uploaded_file.save(filepath)
    return filepath, os.path.basename(filepath), None


def _model_content(db, conversation_id):
    """The reference material the generator works from: every system message in
    the conversation, oldest first. That is the file uploaded when the
    conversation was created, plus anything attached to a later message."""
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role == "system")
        .order_by(Message.id.asc())
    ).all()
    return "\n\n".join(row.content for row in rows if row.content)


def mode3_chat(db, apology, conversation_id, file_read, upload_folder, allowed_file):

    conversation = db.scalars(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == session["user_id"])
    ).first()

    if not conversation:
        return apology("conversație inexistentă")

    # Exclude hidden system messages from display
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role != "system")
        .order_by(Message.id.asc())
    ).all()

    # Count ALL messages (including system) to check if first load
    total = db.scalar(select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id))

    if total == 0:
        filename = conversation.title
        filepath = os.path.join(upload_folder, filename)

        if not os.path.exists(filepath):
            return apology("Fișierul încărcat nu a fost găsit", 404)

        raw_content = file_read(filepath)

        latex_content = ai.convert_file_to_latex(raw_content, filepath=filepath)

        # Store PURE LaTeX as hidden system message (model reference for generation)
        db.add(Message(conversation_id=conversation_id, role="system", content=latex_content))

        if latex_content and latex_content.startswith("Eroare AI:"):
            intro = (
                f"Am încercat să citesc fișierul **{filename}**, "
                f"dar a apărut o eroare la procesare:\n\n{latex_content}\n\n"
                f"Poți încerca să încarci din nou fișierul."
            )
        else:
            intro = (
                f"Am citit fișierul **{filename}** și am identificat "
                f"următoarele exerciții:\n\n{latex_content}\n\n"
                f"Verifică dacă exercițiile au fost extrase corect.\n"
                f"- Dacă totul arată bine, scrie **\"generează testul\"**\n"
                f"- Dacă sunt probleme, descrie ce trebuie corectat."
            )

        # Store visible intro
        db.add(Message(conversation_id=conversation_id, role="assistant", content=intro))
        db.commit()
        return redirect(f"/mode3/{conversation_id}")

    if request.method == "POST":
        prompt = (request.form.get("prompt") or "").strip()

        # A file attached to this message becomes extra reference material:
        # read it, convert it to LaTeX the same way the conversation's original
        # model was, and store it as another hidden system message.
        filepath, filename, attach_error = _save_attachment(
            upload_folder, request.files.get("file"), allowed_file
        )

        if attach_error:
            return apology(f"{attach_error}. Folosește .pdf, .docx, .txt, .png, .jpg sau .jpeg.", 400)

        if not prompt and not filename:
            return redirect(f"/mode3/{conversation_id}")

        if filename:
            attachment_latex = ai.convert_file_to_latex(file_read(filepath), filepath=filepath)
            db.add(Message(
                conversation_id=conversation_id,
                role="system",
                content=f"MODEL SUPLIMENTAR ({filename}):\n{attachment_latex}",
            ))
            prompt = f"[Fișier atașat: {filename}]\n{prompt}".strip()

        db.add(Message(conversation_id=conversation_id, role="user", content=prompt))
        db.commit()

        # Build history (exclude system message)
        history_rows = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role != "system")
            .order_by(Message.id.asc())
        ).all()
        history = "\n".join(f"{r.role}: {r.content}" for r in history_rows)

        # Fetch the pure LaTeX model (the hidden system messages)
        model_content = _model_content(db, conversation_id)

        response = ai.generate_from_model(
            model_content=model_content,
            conversation_history=history,
            user_prompt=prompt
        )

        db.add(Message(conversation_id=conversation_id, role="assistant", content=response))
        db.commit()
        return redirect(f"/mode3/{conversation_id}")

    # ---- GET: render chat ----
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == "mode3")
        .order_by(Conversation.created_at.desc())
    ).all()

    return render_template(
        "modes/mode3.html",
        messages=messages,
        conversations=conversations,
        conversation=conversation,
        conversation_id=conversation_id
    )


def mode4_chat(db, apology, conversation_id, upload_folder, allowed_file):

    conversation = db.scalars(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == session["user_id"])
    ).first()

    if not conversation:
        return apology("conversație inexistentă")

    # Exclude hidden system message (raw transcription) from display
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role != "system")
        .order_by(Message.id.asc())
    ).all()

    total = db.scalar(select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id))

    if total == 0:
        filename = conversation.title
        filepath = os.path.join(upload_folder, filename)

        if not os.path.exists(filepath):
            return apology("Poza încărcată nu a fost găsită", 404)

        latex_content = ai.transcribe_handwriting(filepath)

        # Store PURE LaTeX as hidden system message (model reference for generation)
        db.add(Message(conversation_id=conversation_id, role="system", content=latex_content))

        if latex_content and latex_content.startswith("Eroare AI:"):
            intro = (
                f"Am încercat să citesc poza **{filename}**, "
                f"dar a apărut o eroare la procesare:\n\n{latex_content}\n\n"
                f"Poți încerca să încarci din nou fișierul."
            )
        else:
            intro = (
                f"Am transcris exercițiile scrise de mână din **{filename}**:\n\n{latex_content}\n\n"
                f"Verifică dacă transcrierea este corectă.\n"
                f"- Dacă totul arată bine, scrie **\"generează testul\"** sau cere o variantă nouă\n"
                f"- Dacă ceva a fost citit greșit, descrie ce trebuie corectat."
            )

        # Store visible intro
        db.add(Message(conversation_id=conversation_id, role="assistant", content=intro))
        db.commit()
        return redirect(f"/mode4/{conversation_id}")

    if request.method == "POST":
        prompt = (request.form.get("prompt") or "").strip()

        # A photo/PDF attached to this message is transcribed the same way the
        # conversation's first upload was, and kept as another hidden system
        # message so later prompts can still refer back to it.
        filepath, filename, attach_error = _save_attachment(
            upload_folder, request.files.get("file"), allowed_file
        )

        if attach_error:
            return apology(f"{attach_error}. Folosește o poză .png/.jpg sau un .pdf.", 400)

        if not prompt and not filename:
            return redirect(f"/mode4/{conversation_id}")

        if filename:
            attachment_latex = ai.transcribe_handwriting(filepath, extra_instructions=prompt or None)
            db.add(Message(
                conversation_id=conversation_id,
                role="system",
                content=f"TRANSCRIERE SUPLIMENTARĂ ({filename}):\n{attachment_latex}",
            ))
            prompt = f"[Fișier atașat: {filename}]\n{prompt}".strip()

        db.add(Message(conversation_id=conversation_id, role="user", content=prompt))
        db.commit()

        # Build history (exclude system message)
        history_rows = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role != "system")
            .order_by(Message.id.asc())
        ).all()
        history = "\n".join(f"{r.role}: {r.content}" for r in history_rows)

        # Fetch the pure LaTeX transcription (the hidden system messages)
        model_content = _model_content(db, conversation_id)

        response = ai.generate_from_model(
            model_content=model_content,
            conversation_history=history,
            user_prompt=prompt
        )

        db.add(Message(conversation_id=conversation_id, role="assistant", content=response))
        db.commit()
        return redirect(f"/mode4/{conversation_id}")

    # ---- GET: render chat ----
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == "mode4")
        .order_by(Conversation.created_at.desc())
    ).all()

    return render_template(
        "modes/mode4.html",
        messages=messages,
        conversations=conversations,
        conversation=conversation,
        conversation_id=conversation_id,
        **{"class": conversation["school_class"] if "school_class" in conversation.keys() else "—"},
        bac=conversation["bac"] if "bac" in conversation.keys() else "—"
    )


def mode2_chat(db, apology, conversation_id):

    # ---- Load conversation + joined style description ----
    conversation = db.scalars(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == session["user_id"])
    ).first()

    if not conversation:
        return apology("conversație inexistentă")

    # ---- Insert intro message ONLY on first load ----
    existing_count = db.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )

    if existing_count == 0:

        style_desc = conversation["style_description"] or "Stil implicit"
        school_class = conversation["school_class"] or "—"
        bac = conversation["bac"] or "—"

        intro = (
            f"Stilul tău activ este:\n"
            f"- {style_desc}\n"
            f"- Clasa: {school_class}\n"
            f"- BAC: {bac}\n\n"
            f"Scrie exercițiile în limbaj natural, "
            f"iar eu le voi transforma în limbaj matematic gata de printat."
        )

        db.add(Message(conversation_id=conversation_id, role="assistant", content=intro))
        db.commit()

    # ---- Handle user POST ----
    if request.method == "POST":

        prompt = request.form.get("prompt")
        action_type = request.form.get("action_type", "normal")

        if not prompt or not prompt.strip():
            return redirect(f"/mode2/{conversation_id}")

        # save user message
        db.add(Message(conversation_id=conversation_id, role="user", content=prompt))
        db.commit()

        # ---- AI response: pick the right pipeline ----
        if action_type == "generate":
            n_raw = request.form.get("exercise_count", "5")
            try:
                n = int(n_raw)
            except (TypeError, ValueError):
                n = 5
            n = max(1, min(n, 50))  # sanity cap

            response = adjacent.generate_exercises_free(
                n,
                conversation["style_description"],
                conversation["school_class"],
                conversation["bac"]
            )

        elif action_type == "solve":
            response = adjacent.solve_step_by_step(
                prompt,
                conversation["style_description"],
                conversation["school_class"],
                conversation["bac"]
            )

        else:  # "normal" -> textarea input, keep strict translate_math
            response = ai.translate_math(
                prompt,
                conversation["style_description"],
                conversation["school_class"],
                conversation["bac"]
            )

        # save assistant message
        db.add(Message(conversation_id=conversation_id, role="assistant", content=response))
        db.commit()

        # update title with first user prompt (optional, like mode1)
        if conversation.title in ("Traducere nouă", None, ""):
            short_title = prompt.strip().split("\n")[0][:40]
            conversation.title = short_title
            db.commit()

        return redirect(f"/mode2/{conversation_id}")

    # ---- Load messages + sidebar conversations ----
    messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
    ).all()

    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == "mode2")
        .order_by(Conversation.created_at.desc())
    ).all()

    return render_template(
        "modes/mode2.html",
        messages=messages,
        conversations=conversations,
        conversation=conversation,
        conversation_id=conversation_id
    )

def mode1_chat(db, apology, conversation_id):
    conversation = db.scalars(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == session["user_id"])
    ).first()

    if not conversation:
        return apology("conversation not found")

    if request.method == "POST":

        prompt = request.form.get("prompt")
        if not prompt:
            return redirect(f"/mode1/{conversation_id}")

        if conversation.title == "Conversație nouă":
            new_title = prompt[:40]
            conversation.title = new_title
            db.commit()

        # save user msg
        db.add(Message(conversation_id=conversation_id, role="user", content=prompt))
        db.commit()

        # AI RESPONSE
        history_rows = db.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
        ).all()

        history = [
            {
                "role": row.role,
                "content": row.content
            }
            for row in history_rows
        ]
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        if conversation.title == "Ghid Website":
            response = ai.website_guide(prompt)
        else:
            response = ai.assistant(prompt)
        response_html=markdown.markdown(response)

        # save ai msg
        db.add(Message(conversation_id=conversation_id, role="assistant", content=response))
        db.commit()

        return redirect(f"/mode1/{conversation_id}")

    messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
    ).all()
    messages = [
        dict(m) | {"content": markdown.markdown(m["content"])}
        for m in messages
    ]
    #outputs first message
    if len(messages) == 0:
        if conversation.title == "Ghid Website":
            intro = """Spune-mi situația actuală a unei clase la care predai? Pot să te îndrum în website pas cu pas în funcție de ce îți dorești să faci astăzi."""
        else:
            intro = """Sunt un asistent virtual specializat în matematică...

    Pot ajuta cu:
    - Matematică
    - Predare
    - Gestionarea elevilor
    - Explicații
    - Exerciții

    Cu ce te pot ajuta astăzi?"""

        db.add(Message(conversation_id=conversation_id, role="assistant", content=intro))
        db.commit()

        return redirect(f"/mode1/{conversation_id}")
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == "mode1")
        .order_by(Conversation.created_at.desc())
    ).all()

    #content= markdown.markdown("row["content"]")
    return render_template("modes/mode1.html",
        messages=messages,
        conversations=conversations,
        conversation_id=conversation_id
    )
# def mode2_chat(db, connect, apology, conversation_id):

#     conversation = db.execute(
#         """
#         SELECT conversations.*, styles.style_description FROM conversations
#         LEFT JOIN styles ON conversations.style_id = styles.id
#         WHERE conversations.id = ? AND conversations.user_id = ?
#         """,
#         (conversation_id, session["user_id"])
#     ).fetchone()

#     if not conversation:
#         return apology("conversatie inexistenta")

#     # =====================================
#     # FIRST MESSAGE AUTO
#     # =====================================

#     messages = db.execute(
#         """
#         SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC
#         """,
#         (conversation_id,)
#     ).fetchall()



#     # =====================================
#     # USER MESSAGE
#     # =====================================

#     if request.method == "POST":

#         prompt = request.form.get("prompt")

#         if not prompt:
#             return redirect(f"/mode2/{conversation_id}")

#         # save user msg
#         db.execute(
#             """
#             INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)
#             """,
#             (conversation_id, "user", prompt)
#         )

#         connect.commit()

#         # AI RESPONSE
#         response = ai.translate_math(
#             prompt,
#             conversation["style_description"],
#             conversation["school_class"],
#             conversation["bac"]
#         )

#         # save ai msg
#         db.execute(
#             """
#             INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)
#             """,
#             (conversation_id, "assistant", response)
#         )

#         connect.commit()

#         return redirect(f"/mode2/{conversation_id}")

#     # =====================================
#     # LOAD MESSAGES
#     # =====================================

#     messages = db.execute(
#         """
#         SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC
#         """,
#         (conversation_id,)
#     ).fetchall()

#     conversations = db.execute(
#         """
#         SELECT * FROM conversations WHERE user_id = ? AND mode = ? ORDER BY created_at DESC
#         """,
#         (session["user_id"], "mode2")
#     ).fetchall()

#     return render_template("modes/mode2.html", messages=messages, conversations=conversations, conversation=conversation, conversation_id=conversation_id)
