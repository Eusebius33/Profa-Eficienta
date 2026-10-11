import markdown
import os
from flask import request, redirect, render_template, session, jsonify
from sqlalchemy import select, func
from werkzeug.utils import secure_filename
from secondary import ai
from secondary import adjacent
from models import Conversation, Message


def _wants_json():
    """True when the chat form posted through fetch rather than the browser.

    The async path and the plain form post share one handler: this decides
    whether to answer with the new turn as JSON or with the old redirect, so
    the modes keep working with scripting unavailable.
    """
    return request.headers.get("X-Requested-With") == "fetch"


def _render_turns(partial, messages, fresh=True):
    """Render a run of messages with a mode's single-turn partial."""
    return "".join(
        render_template(partial, message=m, fresh=fresh) for m in messages
    )


def _turn_response(partial, messages, redirect_to, fresh=True):
    """Answer a chat POST: the rendered turn for fetch, a redirect otherwise."""
    if _wants_json():
        return jsonify(ok=True, html=_render_turns(partial, messages, fresh=fresh))
    return redirect(redirect_to)


def _json_error(message, redirect_to, status=400):
    if _wants_json():
        return jsonify(ok=False, error=message), status
    return redirect(redirect_to)


# Quick-action prompts live here, not in the page. The buttons used to build
# these client side and paste the whole previous answer into the textarea,
# which is why the teacher saw a wall of text appear before anything sent --
# and why "rândul 2" only ever produced a single exercise: nothing told the
# model to work through the test item by item.
QUICK_ACTIONS = {
    "solve_test": (
        "Rezolvă complet, pas cu pas, FIECARE exercițiu din testul de mai jos. "
        "Păstrează numerotarea originală a exercițiilor. Pentru fiecare exercițiu "
        "arată raționamentul și răspunsul final, clar marcat."
    ),
    "generate_row_2": (
        "Creează RÂNDUL 2 al testului de mai jos.\n"
        "Reguli obligatorii:\n"
        "- Parcurge testul exercițiu cu exercițiu și înlocuiește FIECARE exercițiu "
        "cu unul nou.\n"
        "- Rezultatul trebuie să conțină EXACT același număr de exerciții ca "
        "originalul și aceeași numerotare.\n"
        "- Fiecare exercițiu nou testează aceeași noțiune și are aceeași "
        "dificultate ca exercițiul din original aflat pe aceeași poziție, dar cu "
        "alte numere/date, astfel încât răspunsurile să difere.\n"
        "- Păstrează structura, punctajul și formularea generală a testului.\n"
        "- NU rezolva exercițiile; livrează doar enunțurile rândului 2."
    ),
    "generate_similar": (
        "Creează un test NOU după modelul testului de mai jos.\n"
        "Reguli obligatorii:\n"
        "- Parcurge modelul exercițiu cu exercițiu și generează, pentru FIECARE, "
        "un exercițiu nou pe aceeași temă și de aceeași dificultate.\n"
        "- Păstrează exact numărul de exerciții, numerotarea, structura și "
        "punctajul modelului.\n"
        "- Schimbă datele numerice și contextul, ca răspunsurile să fie diferite "
        "de cele ale modelului.\n"
        "- NU rezolva exercițiile; livrează doar enunțurile."
    ),
}

# Mode 1 is a free conversation, so its quick actions refer to what was just
# said rather than to an uploaded model.
CHAT_ACTIONS = {
    "solve": (
        "Rezolvă complet, pas cu pas, exercițiul din mesajul anterior al conversației. "
        "Arată raționamentul și marchează clar răspunsul final. Dacă în mesajul anterior "
        "sunt mai multe exerciții, rezolvă-le pe toate, păstrând numerotarea."
    ),
    "generate_similar": (
        "Generează 5 exerciții noi, similare cu cel din mesajul anterior: aceeași noțiune "
        "și aceeași dificultate, dar cu alte date numerice. Numerotează-le de la 1 la 5 și "
        "NU le rezolva."
    ),
    "teach_class": (
        "Explică-mi cum predau la clasă noțiunea din discuția de mai sus. Structurează "
        "răspunsul astfel: 1) ideea de bază în cuvinte simple, 2) un exemplu lucrat, "
        "3) greșelile frecvente ale elevilor și cum le previn, 4) două exerciții de fixare."
    ),
}

CHAT_ACTION_LABELS = {
    "solve": "Soluție exercițiu anterior",
    "generate_similar": "Generează exerciții similare",
    "teach_class": "Cum predau la clasă",
}


# What the teacher sees in the transcript for a quick action: the intent, not
# the several-hundred-word instruction that goes to the model.
QUICK_ACTION_LABELS = {
    "solve_test": "Rezolvare test",
    "generate_row_2": "Generează rândul 2",
    "generate_similar": "Creează după model",
}


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


def _seed_instructions(db, conversation_id):
    """Run the instructions typed on /menu as the conversation's opening turn.

    The mode-3/mode-4 cards on /menu collect one "Instrucțiuni și diferențe față
    de model" field. /create_modeN stashes it here because the conversation does
    not exist yet at that point; this replays it as the first user message once
    the uploaded model has been read, so the teacher lands on a generated test
    instead of having to retype what they already asked for.
    """
    instructions = (session.pop(f"mode_instructions_{conversation_id}", "") or "").strip()
    if not instructions:
        return

    db.add(Message(conversation_id=conversation_id, role="user", content=instructions))
    db.commit()

    history_rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role != "system")
        .order_by(Message.id.asc())
    ).all()
    history = "\n".join(f"{r.role}: {r.content}" for r in history_rows)

    response = ai.generate_from_model(
        model_content=_model_content(db, conversation_id),
        conversation_history=history,
        user_prompt=instructions,
    )

    db.add(Message(conversation_id=conversation_id, role="assistant", content=response))
    db.commit()


def mode3_bootstrap(db, apology, conversation_id, file_read, upload_folder):
    """Read the uploaded model for a brand-new mode-3 conversation.

    Same move as mode 4: this used to run inside the first GET, so the teacher
    waited on /menu through the file conversion and any instructions typed on
    the card. The conversation opens first and this fills it in.
    """
    conversation = db.scalars(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == session["user_id"]
        )
    ).first()

    if not conversation:
        return jsonify(ok=False, error="Conversație inexistentă"), 404

    total = db.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )

    if total:
        existing = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role != "system")
            .order_by(Message.id.asc())
        ).all()
        return jsonify(ok=True, html=_render_turns("partials/mode3_message.html", existing))

    filename = conversation.title
    filepath = os.path.join(upload_folder, filename)

    if not os.path.exists(filepath):
        return jsonify(ok=False, error="Fișierul încărcat nu a fost găsit"), 404

    try:
        raw_content = file_read(filepath)
        latex_content = ai.convert_file_to_latex(raw_content, filepath=filepath)
    except Exception as exc:  # noqa: BLE001 - surfaced to the teacher verbatim
        return jsonify(
            ok=False,
            error=f"Fișierul nu a putut fi citit ({exc.__class__.__name__}). Încarcă din nou modelul.",
        ), 422

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

    db.add(Message(conversation_id=conversation_id, role="assistant", content=intro))
    db.commit()
    _seed_instructions(db, conversation_id)

    fresh = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role != "system")
        .order_by(Message.id.asc())
    ).all()

    return jsonify(ok=True, html=_render_turns("partials/mode3_message.html", fresh))


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

    if request.method == "POST":
        action_type = (request.form.get("action_type") or "normal").strip()
        prompt = (request.form.get("prompt") or "").strip()

        # A file attached to this message becomes extra reference material:
        # read it, convert it to LaTeX the same way the conversation's original
        # model was, and store it as another hidden system message.
        filepath, filename, attach_error = _save_attachment(
            upload_folder, request.files.get("file"), allowed_file
        )

        if attach_error:
            msg = f"{attach_error}. Folosește .pdf, .docx, .txt, .png, .jpg sau .jpeg."
            if _wants_json():
                return jsonify(ok=False, error=msg), 400
            return apology(msg, 400)

        quick_instruction = QUICK_ACTIONS.get(action_type)

        if quick_instruction:
            if not total:
                return _json_error("Nu există încă niciun model citit.", f"/mode3/{conversation_id}")
            prompt = QUICK_ACTION_LABELS.get(action_type, action_type)
            model_prompt = f"{quick_instruction}\n\nTESTUL:\n{_model_content(db, conversation_id)}"
        else:
            if not prompt and not filename:
                return _json_error("Mesaj gol.", f"/mode3/{conversation_id}")
            model_prompt = prompt

        if filename:
            attachment_latex = ai.convert_file_to_latex(file_read(filepath), filepath=filepath)
            db.add(Message(
                conversation_id=conversation_id,
                role="system",
                content=f"MODEL SUPLIMENTAR ({filename}):\n{attachment_latex}",
            ))
            prompt = f"[Fișier atașat: {filename}]\n{prompt}".strip()
            model_prompt = prompt

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
            user_prompt=model_prompt
        )

        assistant_message = Message(conversation_id=conversation_id, role="assistant", content=response)
        db.add(assistant_message)
        db.commit()

        return _turn_response(
            "partials/mode3_message.html",
            [assistant_message],
            f"/mode3/{conversation_id}",
        )

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
        conversation_id=conversation_id,
        bootstrap_url=(f"/mode3/{conversation_id}/bootstrap" if total == 0 else None),
    )


def mode4_bootstrap(db, apology, conversation_id, upload_folder):
    """Read the uploaded photo/PDF for a brand-new mode-4 conversation.

    This used to run inside the first GET of /mode4/<id>, so the teacher stared
    at /menu for the whole transcription (and again for any instructions typed
    on the card). The page now renders immediately with a skeleton and calls
    this, so the conversation is open while the handwriting is being read.
    """
    conversation = db.scalars(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == session["user_id"]
        )
    ).first()

    if not conversation:
        return jsonify(ok=False, error="Conversație inexistentă"), 404

    total = db.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )

    # Already transcribed -- a double-submit or a reload mid-flight. Hand back
    # what is there rather than paying for the model a second time.
    if total:
        existing = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role != "system")
            .order_by(Message.id.asc())
        ).all()
        return jsonify(ok=True, html=_render_turns("partials/mode4_message.html", existing))

    filename = conversation.title
    filepath = os.path.join(upload_folder, filename)

    if not os.path.exists(filepath):
        return jsonify(ok=False, error="Poza încărcată nu a fost găsită"), 404

    # A corrupt or truncated upload makes the reader raise. Before this ran
    # asynchronously it took the whole page down; now it would strand the
    # skeleton, so it is reported as a normal failed turn instead.
    try:
        latex_content = ai.transcribe_handwriting(filepath)
    except Exception as exc:  # noqa: BLE001 - surfaced to the teacher verbatim
        return jsonify(
            ok=False,
            error=f"Fișierul nu a putut fi citit ({exc.__class__.__name__}). Încarcă din nou poza sau PDF-ul.",
        ), 422

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

    db.add(Message(conversation_id=conversation_id, role="assistant", content=intro))
    db.commit()
    _seed_instructions(db, conversation_id)

    fresh = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role != "system")
        .order_by(Message.id.asc())
    ).all()

    return jsonify(ok=True, html=_render_turns("partials/mode4_message.html", fresh))


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

    if request.method == "POST":
        action_type = (request.form.get("action_type") or "normal").strip()
        prompt = (request.form.get("prompt") or "").strip()

        # A photo/PDF attached to this message is transcribed the same way the
        # conversation's first upload was, and kept as another hidden system
        # message so later prompts can still refer back to it.
        filepath, filename, attach_error = _save_attachment(
            upload_folder, request.files.get("file"), allowed_file
        )

        if attach_error:
            if _wants_json():
                return jsonify(ok=False, error=f"{attach_error}. Folosește o poză .png/.jpg sau un .pdf."), 400
            return apology(f"{attach_error}. Folosește o poză .png/.jpg sau un .pdf.", 400)

        # A quick action carries no typed prompt: the instruction is built here
        # so the button never has to stuff it into the teacher's textarea.
        quick_instruction = QUICK_ACTIONS.get(action_type)

        if quick_instruction:
            if not total:
                return _json_error(
                    "Nu există încă nicio transcriere.", f"/mode4/{conversation_id}"
                )
            display = QUICK_ACTION_LABELS.get(action_type, action_type)
            prompt = display
            model_prompt = f"{quick_instruction}\n\nTESTUL:\n{_model_content(db, conversation_id)}"
        else:
            if not prompt and not filename:
                return _json_error("Mesaj gol.", f"/mode4/{conversation_id}")
            model_prompt = prompt

        if filename:
            attachment_latex = ai.transcribe_handwriting(filepath, extra_instructions=prompt or None)
            db.add(Message(
                conversation_id=conversation_id,
                role="system",
                content=f"TRANSCRIERE SUPLIMENTARĂ ({filename}):\n{attachment_latex}",
            ))
            prompt = f"[Fișier atașat: {filename}]\n{prompt}".strip()
            model_prompt = prompt

        user_message = Message(conversation_id=conversation_id, role="user", content=prompt)
        db.add(user_message)
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
            user_prompt=model_prompt
        )

        assistant_message = Message(conversation_id=conversation_id, role="assistant", content=response)
        db.add(assistant_message)
        db.commit()

        # The user's bubble is already on screen from the optimistic send, so
        # only the answer comes back over fetch.
        return _turn_response(
            "partials/mode4_message.html",
            [assistant_message],
            f"/mode4/{conversation_id}",
        )

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
        # Nothing transcribed yet: the page paints now and the browser kicks
        # off the transcription against this endpoint.
        bootstrap_url=(f"/mode4/{conversation_id}/bootstrap" if total == 0 else None),
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

        # Class and BAC profile are no longer asked for when a mode2
        # conversation is created, so they were only ever rendering as "—".
        # An empty field tells the teacher nothing, so the intro names the
        # active style and nothing else.
        intro = (
            f"Stilul tău activ este:\n"
            f"- {style_desc}\n\n"
            f"Scrie exercițiile în limbaj natural, "
            f"iar eu le voi transforma în limbaj matematic gata de printat."
        )

        db.add(Message(conversation_id=conversation_id, role="assistant", content=intro))
        db.commit()

    # ---- Handle user POST ----
    if request.method == "POST":

        prompt = (request.form.get("prompt") or "").strip()
        action_type = (request.form.get("action_type") or "normal").strip()

        # "Soluție exercițiu anterior" used to ship the previous bubble's text
        # back from the page. The server already has the transcript, so it
        # reads the last exercise itself and the button stays a button.
        # What the solver is handed, when that differs from what the teacher
        # sees in the transcript.
        target = prompt

        if action_type == "solve" and not prompt:
            previous = db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id, Message.role == "user")
                .order_by(Message.id.desc())
                .limit(1)
            ).first()
            if not previous:
                return _json_error("Nu există niciun exercițiu anterior.", f"/mode2/{conversation_id}")
            target = previous.content
            # The bubble says what was asked for, not a second copy of the
            # exercise -- and it matches what the page showed optimistically.
            prompt = CHAT_ACTION_LABELS["solve"]

        if action_type == "generate" and not prompt:
            prompt = f"Generează {request.form.get('exercise_count', '5')} exerciții noi."
            target = prompt

        if not prompt:
            return _json_error("Mesaj gol.", f"/mode2/{conversation_id}")

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
                target,
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
        assistant_message = Message(conversation_id=conversation_id, role="assistant", content=response)
        db.add(assistant_message)
        db.commit()

        # update title with first user prompt (optional, like mode1)
        if conversation.title in ("Traducere nouă", None, ""):
            short_title = prompt.strip().split("\n")[0][:40]
            conversation.title = short_title
            db.commit()

        return _turn_response(
            "partials/mode2_message.html",
            [assistant_message],
            f"/mode2/{conversation_id}",
        )

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

def _mode1_view(message):
    """A mode-1 turn as the template wants it: markdown already rendered."""
    return dict(message) | {"content": markdown.markdown(message["content"])}


def mode1_chat(db, apology, conversation_id):
    conversation = db.scalars(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == session["user_id"])
    ).first()

    if not conversation:
        return apology("conversation not found")

    if request.method == "POST":

        action_type = (request.form.get("action_type") or "normal").strip()
        prompt = (request.form.get("prompt") or "").strip()

        # A quick action's instruction is built here, so the button no longer
        # has to paste several hundred words into the teacher's textarea.
        quick_instruction = CHAT_ACTIONS.get(action_type)
        if quick_instruction:
            prompt = CHAT_ACTION_LABELS.get(action_type, action_type)
            model_prompt = quick_instruction
        else:
            if not prompt:
                return _json_error("Mesaj gol.", f"/mode1/{conversation_id}")
            model_prompt = prompt

        if conversation.title == "Conversație nouă":
            conversation.title = prompt[:40]
            db.commit()

        db.add(Message(conversation_id=conversation_id, role="user", content=prompt))
        db.commit()

        # AI RESPONSE
        history_rows = db.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
        ).all()

        history = "\n".join(f"{row.role}: {row.content}" for row in history_rows)
        # The quick action's real instruction rides at the end, after the
        # transcript it refers back to.
        full_prompt = history if model_prompt == prompt else f"{history}\n\nINSTRUCȚIUNE: {model_prompt}"

        if conversation.title == "Ghid Website":
            response = ai.website_guide(full_prompt)
        else:
            response = ai.assistant(full_prompt)

        assistant_message = Message(conversation_id=conversation_id, role="assistant", content=response)
        db.add(assistant_message)
        db.commit()

        return _turn_response(
            "partials/mode1_message.html",
            [_mode1_view(assistant_message)],
            f"/mode1/{conversation_id}",
        )

    messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
    ).all()
    messages = [_mode1_view(m) for m in messages]

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
