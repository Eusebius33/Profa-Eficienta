import markdown
import os
from flask import request, redirect, render_template, session
from secondary import ai
def mode3_chat(db, connect, apology, conversation_id, file_read, upload_folder):

    conversation = db.execute(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, session["user_id"])
    ).fetchone()

    if not conversation:
        return apology("conversație inexistentă")

    # Exclude hidden system messages from display
    messages = db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? AND role != 'system' ORDER BY id ASC",
        (conversation_id,)
    ).fetchall()

    # Count ALL messages (including system) to check if first load
    total = db.execute(
        "SELECT COUNT(*) AS c FROM messages WHERE conversation_id = ?",
        (conversation_id,)
    ).fetchone()["c"]

    if total == 0:
        filename = conversation["title"]
        filepath = os.path.join(upload_folder, filename)

        if not os.path.exists(filepath):
            return apology("Fișierul încărcat nu a fost găsit", 404)

        raw_content = file_read(filepath)

        latex_content = ai.convert_file_to_latex(raw_content, filepath=filepath)

        # Store PURE LaTeX as hidden system message (model reference for generation)
        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "system", latex_content)
        )

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
        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "assistant", intro)
        )
        connect.commit()
        return redirect(f"/mode3/{conversation_id}")

    if request.method == "POST":
        prompt = request.form.get("prompt")
        if not prompt or not prompt.strip():
            return redirect(f"/mode3/{conversation_id}")

        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "user", prompt)
        )
        connect.commit()

        # Build history (exclude system message)
        history_rows = db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? AND role != 'system' ORDER BY id ASC",
            (conversation_id,)
        ).fetchall()
        history = "\n".join(f"{r['role']}: {r['content']}" for r in history_rows)

        # Fetch pure LaTeX model (the hidden system message)
        system_msg = db.execute(
            "SELECT content FROM messages WHERE conversation_id = ? AND role = 'system' LIMIT 1",
            (conversation_id,)
        ).fetchone()
        model_content = system_msg["content"] if system_msg else ""

        response = ai.generate_from_model(
            model_content=model_content,
            conversation_history=history,
            user_prompt=prompt
        )

        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "assistant", response)
        )
        connect.commit()
        return redirect(f"/mode3/{conversation_id}")

    # ---- GET: render chat ----
    conversations = db.execute(
        "SELECT * FROM conversations WHERE user_id = ? AND mode = ? ORDER BY created_at DESC",
        (session["user_id"], "mode3")
    ).fetchall()

    return render_template(
        "modes/mode3.html",
        messages=messages,
        conversations=conversations,
        conversation=conversation,
        conversation_id=conversation_id
    )


def mode2_chat(db, connect, apology, conversation_id):

    # ---- Load conversation + joined style description ----
    conversation = db.execute(
        """
        SELECT conversations.*, styles.style_description
        FROM conversations
        LEFT JOIN styles ON conversations.style_id = styles.id
        WHERE conversations.id = ? AND conversations.user_id = ?
        """,
        (conversation_id, session["user_id"])
    ).fetchone()

    if not conversation:
        return apology("conversație inexistentă")

    # ---- Insert intro message ONLY on first load ----
    existing = db.execute(
        "SELECT COUNT(*) AS c FROM messages WHERE conversation_id = ?",
        (conversation_id,)
    ).fetchone()

    if existing["c"] == 0:

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

        db.execute(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, ?, ?)
            """,
            (conversation_id, "assistant", intro)
        )
        connect.commit()

    # ---- Handle user POST ----
    if request.method == "POST":

        prompt = request.form.get("prompt")

        if not prompt or not prompt.strip():
            return redirect(f"/mode2/{conversation_id}")

        # save user message
        db.execute(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, ?, ?)
            """,
            (conversation_id, "user", prompt)
        )
        connect.commit()

        # AI response
        response = ai.translate_math(
            prompt,
            conversation["style_description"],
            conversation["school_class"],
            conversation["bac"]
        )

        # save assistant message
        db.execute(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, ?, ?)
            """,
            (conversation_id, "assistant", response)
        )
        connect.commit()

        # update title with first user prompt (optional, like mode1)
        if conversation["title"] in ("Traducere nouă", None, ""):
            short_title = prompt.strip().split("\n")[0][:40]
            db.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (short_title, conversation_id)
            )
            connect.commit()

        return redirect(f"/mode2/{conversation_id}")

    # ---- Load messages + sidebar conversations ----
    messages = db.execute(
        """
        SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()

    conversations = db.execute(
        """
        SELECT * FROM conversations WHERE user_id = ? AND mode = ? ORDER BY created_at DESC
        """,
        (session["user_id"], "mode2")
    ).fetchall()

    return render_template(
        "modes/mode2.html",
        messages=messages,
        conversations=conversations,
        conversation=conversation,
        conversation_id=conversation_id
    )

def mode1_chat(db, connect, apology, conversation_id):
    conversation = db.execute(
        """
        SELECT * FROM conversations WHERE id = ? AND user_id = ?
        """,
        (conversation_id, session["user_id"])
    ).fetchone()

    if not conversation:
        return apology("conversation not found")

    if request.method == "POST":

        prompt = request.form.get("prompt")
        if not prompt:
            return redirect(f"/mode1/{conversation_id}")

        if conversation["title"] == "Conversație nouă":
            new_title = prompt[:40]
            db.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (new_title, conversation_id)
            )
            connect.commit()

        # save user msg
        db.execute(
            """
            INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)
            """,
            (conversation_id, "user", prompt)
        )

        connect.commit()

        # AI RESPONSE
        history_rows = db.execute(
            """
            SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC
            """,
            (conversation_id,)
        ).fetchall()

        history = [
            {
                "role": row["role"],
                "content": row["content"]
            }
            for row in history_rows
        ]
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        response = ai.assistant(prompt)
        response_html=markdown.markdown(response)

        # save ai msg
        db.execute(
            """
            INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)
            """,
            (conversation_id, "assistant", response)
        )

        connect.commit()

        return redirect(f"/mode1/{conversation_id}")

    messages = db.execute(
        """
        SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()
    messages = [
        dict(m) | {"content": markdown.markdown(m["content"])}
        for m in messages
    ]
    #outputs first message
    if len(messages) == 0:
        intro = """Sunt un asistent virtual specializat în matematică...

    Pot ajuta cu:
    - Matematică
    - Predare
    - Gestionarea elevilor
    - Explicații
    - Exerciții

    Cu ce te pot ajuta astăzi?"""

        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "assistant", intro)
        )
        connect.commit()

        return redirect(f"/mode1/{conversation_id}")
    conversations = db.execute(
        """
        SELECT * FROM conversations WHERE user_id = ? AND mode = ? ORDER BY created_at DESC
        """,
        (session["user_id"], "mode1")
    ).fetchall()

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
