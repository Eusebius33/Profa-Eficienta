import sqlite3
from functools import wraps
import json
import os
from werkzeug.utils import secure_filename
import uuid
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
#import markdown
#mode3
from PyPDF2 import PdfReader
from docx import Document
from secondary import ai, docs, ocr, accounts
from secondary import model_route
from bac_generator.routes import bac_generator_bp
from bac_generator.generator import BACExamGenerator
import traceback

app = Flask(__name__)
app.register_blueprint(bac_generator_bp)
os.makedirs("uploads", exist_ok=True)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['TEMPLATES_AUTO_RELOAD'] = True


Session(app)

def load_translations():
    with open("translations.json", "r", encoding="utf-8") as file:
        return json.load(file)

translations = load_translations()

@app.context_processor
def inject_translations():
    def t(key):
        lang = request.cookies.get("lang", session.get("lang", "ro"))
        return translations.get(key, {}).get(lang, translations.get(key, {}).get("ro", key))

    return {"t": t}

@app.route("/api/translations")
def api_translations():
    return jsonify(load_translations())

@app.after_request
def after_request(response):
    """Prevent browser from caching pages — fixes back-button after logout."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# =========================================================
# DATABASE & TABLES
# =========================================================
#profu.db e data baseu nu proful.db
connect = sqlite3.connect("profu.db", check_same_thread=False)

connect.row_factory = sqlite3.Row

db = connect.cursor()

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hash TEXT NOT NULL,
    username TEXT NOT NULL,
    gender TEXT NOT NULL,
    tehnologie TEXT NOT NULL,
    liceu TEXT NOT NULL
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mode TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    title TEXT,
    style_id TEXT,
    school_class TEXT,
    bac TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS styles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    style_name TEXT NOT NULL,
    test_type TEXT NOT NULL,
    style_description TEXT NOT NULL,

    documents TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

migrations = [
    "ALTER TABLE messages ADD COLUMN action_type TEXT",
    "ALTER TABLE styles ADD COLUMN style_name TEXT",
    "ALTER TABLE conversations ADD COLUMN school_class TEXT",
    "ALTER TABLE conversations ADD COLUMN style_id INTEGER",
    "ALTER TABLE conversations ADD COLUMN bac TEXT",
    "ALTER TABLE messages ADD COLUMN exam_data TEXT",
]


for sql in migrations:
    try:
        db.execute(sql)
    except Exception as e:
        if "duplicate column name" not in str(e).lower():
            raise

# try:
#     db.execute("ALTER TABLE messages ADD COLUMN action_type TEXT")
# except Exception as e:
#     if "duplicate column name" not in str(e).lower():
#         raise
# try:
#     db.execute("ALTER TABLE styles ADD COLUMN style_name TEXT")
# except:
#     pass
# try:
#     db.execute("ALTER TABLE conversations ADD COLUMN style_id INTEGER")
# except:
#     pass

# try:
#     db.execute("ALTER TABLE conversations ADD COLUMN school_class TEXT")
# except:
#     pass

# try:
#     db.execute("ALTER TABLE conversations ADD COLUMN bac TEXT")
# except:
#     pass
connect.commit()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "docx", "txt"}
def allowed_file(filename):

    return ("." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS)

# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session.get("user_id") is None:
            return redirect("/login")

        return f(*args, **kwargs)

    return decorated_function

# =========================================================
# APOLOGY
# =========================================================

def apology(message, code=400):
    return render_template("apology.html", top=code, bottom=message), code

@app.errorhandler(404)
def not_found(e):
    return apology("page not found", 404)

@app.errorhandler(403)
def forbidden(e):
    return apology("access forbidden", 403)

@app.errorhandler(500)
def server_error(e):
    return apology("an unexpected error occurred", 500)

# =========================================================
# LANDING
# =========================================================

@app.route("/landing")
def landing():
    return render_template("landing.html")
    #TODO
# =========================================================
# INDEX
# =========================================================

@app.route("/")
@login_required
def index():
    return render_template("index.html")

# =========================================================
# REGISTER
# =========================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    return accounts.register_function(db, connect, apology)
# =========================================================
# LOGIN
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    return accounts.login_function(db, apology)
# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
# =========================================================
# ACCOUNT
# =========================================================
@app.route("/account")
@login_required
def account():
    return accounts.account_function(db)
# =========================================================
# PASSWORD CHANGE
# =========================================================

@app.route("/passwordchange", methods=["GET", "POST"])
@login_required
def passwordchange():
    #TODO
    return accounts.password_function(db, connect, apology)
# =========================================================
# STYLE
# =========================================================
@app.route("/style", methods=["GET", "POST"])
@login_required
def style():
    return accounts.style_function(apology, db, connect)
    #TODO
# =========================================================
# MENU
# =========================================================
@app.route("/menu")
@login_required
def menu():

    styles = db.execute(
        """
        SELECT * FROM styles WHERE user_id = ? ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    return render_template("menu.html", styles=styles)


@app.route("/documentation", methods=["GET", "POST"])
@login_required
def documentation():

    return render_template("documentation.html")


# =========================================================
# MODE1
# =========================================================
@app.route("/create_mode1", methods=["POST"])
@login_required
def create_mode1():

    db.execute(
        "INSERT INTO conversations (user_id, mode, title) VALUES (?, ?, ?)",
        (session["user_id"], "mode1", "Conversație nouă"))
    connect.commit()
    conversation_id = db.lastrowid
    return redirect(f"/mode1/{conversation_id}")


@app.route("/mode1/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode1(conversation_id):
    return model_route.mode1_chat(db, connect, apology, conversation_id)

# =========================================================
# MODE2
# =========================================================
# =========================================================
# MODE2
# =========================================================
@app.route("/create_mode2", methods=["POST"])
@login_required
def create_mode2():

    style_id = request.form.get("style")
    school_class = request.form.get("school_class")
    bac = request.form.get("bac")

    db.execute(
        """
        INSERT INTO conversations (user_id, mode, title, style_id, school_class, bac) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session["user_id"], "mode2", "Traducere nouă", style_id, school_class, bac)
    )
    connect.commit()

    conversation_id = db.lastrowid
    return redirect(f"/mode2/{conversation_id}")


@app.route("/mode2/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode2(conversation_id):
    return model_route.mode2_chat(db, connect, apology, conversation_id)

# =========================================================
# MODE3
# =========================================================
#TODO
@app.route("/create_mode3", methods=["POST"])
@login_required
def create_mode3():
    uploaded_file = request.files.get("file")

    if not uploaded_file or uploaded_file.filename == "":
        return apology("Niciun fișier încărcat", 400)

    if not allowed_file(uploaded_file.filename):
        return apology("Tip de fișier nepermis", 400)

    filename = secure_filename(uploaded_file.filename)
    os.makedirs("uploads", exist_ok=True)          # ← safety net
    uploaded_file.save(f"uploads/{filename}")
    db.execute(
        """
        INSERT INTO conversations (user_id, mode, title)
        VALUES (?, ?, ?)
        """,
        (session["user_id"], "mode3", filename)
    )

    connect.commit()

    conversation_id = db.lastrowid

    return redirect(f"/mode3/{conversation_id}")

def file_read(filepath):
    extension = os.path.splitext(filepath)[1].lower()

    if extension == ".pdf":
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text if text.strip() else "[PDF scanat - conținut va fi extras la generare]"

    elif extension == ".docx":
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs)

    elif extension == ".txt":
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    return "Unsupported file type"

@app.route("/mode3/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode3(conversation_id):
    return model_route.mode3_chat(db, connect, apology, conversation_id, file_read, "uploads")
#                                                                                    ^^^^^^^^^ add this

# @app.route("/mode3", methods=["GET", "POST"])
# @login_required
# def mode3(conversation_id):
    #TODO
    #if math convert to latex to get shown on first message
    #store and display it as first message in that conversation and ask user if inputs are correct
    #take file/first output as part of the prompt, AI should remember what has been read from the file
    #Auto generate the same number of similar exercises as the file has, 
    #end output with do you want another test or do you want to modify current exercises

    # response = None

    # if request.method == "POST":

    #     prompt = request.form.get("prompt")
    #     differences = request.form.get("differences")
    #     file = file_read()
    #     response = ai.generate_from_model(prompt, differences)

    # return render_template("modes/mode3.html", response=response)



# =========================================================
# MODE4
# =========================================================
#TODO
@app.route("/create_mode4", methods=["GET", "POST"])
@login_required
def create_mode4():

    db.execute(
        """
        INSERT INTO conversations (user_id, mode, title) VALUES (?, ?, ?)
        """,
        (session["user_id"], "mode4", "foaie de mana transcrisa nouă")
    )

    connect.commit()

    conversation_id = db.lastrowid

    return redirect(f"/mode4/{conversation_id}")


@app.route("/mode4")
@login_required
def mode4_latest():
    conversation = db.execute(
        """
        SELECT * FROM conversations WHERE user_id = ? AND mode = ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (session["user_id"], "mode4")
    ).fetchone()

    if not conversation:
        return redirect("/menu")

    return redirect(f"/mode4/{conversation['id']}")


@app.route("/mode4/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode4(conversation_id):
    conversation = db.execute(
        """
        SELECT * FROM conversations WHERE id = ? AND user_id = ? AND mode = ?
        """,
        (conversation_id, session["user_id"], "mode4")
    ).fetchone()

    if not conversation:
        return apology("conversație inexistentă", 404)

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        action_type = request.form.get("action_type", "normal")
        uploaded_file = request.files.get("file")

        response = None

        if uploaded_file and uploaded_file.filename:
            original_name = secure_filename(uploaded_file.filename)
            extension = os.path.splitext(original_name)[1].lower()

            if extension not in [".png", ".jpg", ".jpeg", ".pdf"]:
                return apology("Pentru Mode 4 poți încărca doar PNG, JPG, JPEG sau PDF.", 400)

            os.makedirs("uploads", exist_ok=True)
            filename = f"{uuid.uuid4().hex}_{original_name}"
            filepath = os.path.join("uploads", filename)
            uploaded_file.save(filepath)

            user_message = f"Fișier încărcat: {original_name}"
            if prompt:
                user_message += f"\nInstrucțiuni: {prompt}"

            db.execute(
                """
                INSERT INTO messages (conversation_id, role, content, action_type)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, "user", user_message, action_type)
            )

            response = ocr.extract_handwriting(filepath, prompt)

        elif prompt:
            previous_messages = db.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,)
            ).fetchall()

            last_assistant_message = ""
            for msg in reversed(previous_messages):
                if msg["role"] == "assistant":
                    last_assistant_message = msg["content"]
                    break

            db.execute(
                """
                INSERT INTO messages (conversation_id, role, content, action_type)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, "user", prompt, action_type)
            )

            if last_assistant_message:
                response = ocr.generate_from_transcription(
                    last_assistant_message,
                    prompt,
                    action_type
                )
            else:
                response = ai.assistant(prompt)

        if response:
            db.execute(
                """
                INSERT INTO messages (conversation_id, role, content, action_type)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, "assistant", response, action_type)
            )

        connect.commit()
        return redirect(f"/mode4/{conversation_id}")

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
        (session["user_id"], "mode4")
    ).fetchall()

    return render_template(
        "modes/mode4.html",
        conversations=conversations,
        conversation=conversation,
        messages=messages,
        conversation_id=conversation_id,
        **{"class": conversation["school_class"] if "school_class" in conversation.keys() else "—"},
        bac=conversation["bac"] if "bac" in conversation.keys() else "—"
    )
# =========================================================
# MODE5
# =========================================================
#TODO
@app.route("/create_mode5", methods=["GET", "POST"])
@login_required
def create_mode5():

    db.execute(
        """
        INSERT INTO conversations (user_id, mode, title) VALUES (?, ?, ?)
        """,
        (session["user_id"], "mode5", "Varianta BAC nouă")
    )

    connect.commit()

    conversation_id = db.lastrowid

    # Generate the first BAC variant right away so the user doesn't land on an empty chat
    default_lessons = [
        "Radicali", "Puteri", "Progresii", "Probabilități",
        "Funcții", "Logaritmi", "Numere complexe", "Trigonometrie",
        "Matrici", "Legi de compoziție", "Limite", "Derivate",
        "Integrale definite", "Polinoame",
    ]
    generator = BACExamGenerator()
    exam_data = generator.generate_exam(default_lessons)

    db.execute(
        """
        INSERT INTO messages (conversation_id, role, content, exam_data)
        VALUES (?, ?, ?, ?)
        """,
        (conversation_id, "assistant", exam_data["html_preview"], json.dumps(exam_data))
    )

    connect.commit()

    return redirect(f"/mode5/{conversation_id}")

@app.route("/mode5")
@login_required
def mode5_latest():
    conversation = db.execute(
        """
        SELECT * FROM conversations WHERE user_id = ? AND mode = ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (session["user_id"], "mode5")
    ).fetchone()

    if not conversation:
        return redirect("/menu")

    return redirect(f"/mode5/{conversation['id']}")


@app.route("/mode5/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode5(conversation_id):
    conversation = db.execute(
        """
        SELECT * FROM conversations WHERE id = ? AND user_id = ? AND mode = ?
        """,
        (conversation_id, session["user_id"], "mode5")
    ).fetchone()

    if not conversation:
        return apology("conversație inexistentă", 404)

    if request.method == "POST":
        prompt = request.form.get("prompt")
        if prompt and prompt.strip():
            db.execute(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (?, ?, ?)
                """,
                (conversation_id, "user", prompt)
            )
            connect.commit()

    raw_messages = db.execute(
        """
        SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()

    import markdown
    messages = []
    for msg in raw_messages:
        msg_dict = dict(msg)
        msg_dict["content"] = markdown.markdown(msg_dict["content"])
        if msg_dict.get("exam_data"):
            try:
                msg_dict["exam_data_parsed"] = json.loads(msg_dict["exam_data"])
                if msg_dict["exam_data_parsed"].get("solution_preview"):
                    msg_dict["exam_data_parsed"]["solution_preview"] = markdown.markdown(
                        msg_dict["exam_data_parsed"]["solution_preview"]
                    )
            except Exception:
                msg_dict["exam_data_parsed"] = None
        messages.append(msg_dict)

    conversations = db.execute(
        """
        SELECT * FROM conversations WHERE user_id = ? AND mode = ? ORDER BY created_at DESC
        """,
        (session["user_id"], "mode5")
    ).fetchall()

    return render_template(
        "modes/mode5.html",
        messages=messages,
        conversations=conversations,
        conversation=conversation,
        conversation_id=conversation_id,
        bac=conversation["bac"] if "bac" in conversation.keys() else "M3"
    )

# =========================================================
# CONVERSATION ACTIONS: RENAME / DELETE
# =========================================================

@app.route("/conversation/<int:conversation_id>/rename", methods=["POST"])
@login_required
def rename_conversation(conversation_id):
    new_title = request.form.get("new_title", "").strip()

    if not new_title:
        return apology("Titlul conversației nu poate fi gol.", 400)

    conversation = db.execute(
        """
        SELECT * FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (conversation_id, session["user_id"])
    ).fetchone()

    if not conversation:
        return apology("Conversație inexistentă.", 404)

    db.execute(
        """
        UPDATE conversations
        SET title = ?
        WHERE id = ? AND user_id = ?
        """,
        (new_title, conversation_id, session["user_id"])
    )
    connect.commit()

    return redirect(f"/{conversation['mode']}/{conversation_id}")


@app.route("/conversation/<int:conversation_id>/delete", methods=["POST"])
@login_required
def delete_conversation(conversation_id):
    conversation = db.execute(
        """
        SELECT * FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (conversation_id, session["user_id"])
    ).fetchone()

    if not conversation:
        return apology("Conversație inexistentă.", 404)

    mode = conversation["mode"]

    db.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    db.execute(
        """
        DELETE FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (conversation_id, session["user_id"])
    )

    connect.commit()

    next_conversation = db.execute(
        """
        SELECT * FROM conversations
        WHERE user_id = ? AND mode = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (session["user_id"], mode)
    ).fetchone()

    if next_conversation:
        return redirect(f"/{mode}/{next_conversation['id']}")

    return redirect("/menu")
# =========================================================
# RUN (Reloaded to refresh translations JSON keys)
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)
