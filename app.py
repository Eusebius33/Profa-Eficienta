import sqlite3
from functools import wraps
import json
import os
from types import SimpleNamespace
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


def _normalize_lang(lang):
    if lang in {"ro", "en"}:
        return lang
    return "ro"


def _humanize_key(key):
    if not key:
        return ""
    text = str(key).replace("_", " ")
    text = text.replace("ai", "AI")
    text = text.replace("bac", "BAC")
    return text.strip().title()


@app.before_request
def apply_language():
    lang = _normalize_lang(request.args.get("lang") or request.cookies.get("lang") or session.get("lang") or "ro")
    session["lang"] = lang


@app.context_processor
def inject_translations():
    def t(key):
        lang = _normalize_lang(request.cookies.get("lang") or session.get("lang") or "ro")
        session["lang"] = lang
        entry = translations.get(key, {})
        if isinstance(entry, dict):
            if lang in entry:
                return entry[lang]
            if "ro" in entry:
                return entry["ro"]
        return _humanize_key(key)

    def _(key):
        lang = _normalize_lang(request.cookies.get("lang") or session.get("lang") or "ro")
        session["lang"] = lang
        entry = translations.get(key, {})
        if isinstance(entry, dict):
            if lang in entry:
                return entry[lang]
            if "ro" in entry:
                return entry["ro"]
        return _humanize_key(key) or key

    return {"t": t, "_": _}

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

@app.route("/chat")
@app.route("/chat/<int:conversation_id>")
def chat(conversation_id=None):
    if conversation_id is not None:
        return redirect(f"/mode1/{conversation_id}")
    return redirect("/dashboard")

@app.route("/text_to_math")
def text_to_math():
    return redirect("/menu")

@app.route("/upload_to_math")
def upload_to_math():
    return redirect("/menu")

@app.route("/bac_generator")
def bac_generator():
    return redirect("/menu")

@app.route("/conversations")
def conversations():
    return redirect("/dashboard")

@app.route("/materials")
def materials():
    return redirect("/dashboard")

@app.route("/handwriting_ocr")
def handwriting_ocr():
    return redirect("/menu")

@app.route("/materials/<int:id>/edit")
def edit_material(id):
    return redirect("/dashboard")

@app.route("/materials/<int:id>/download")
def download_material(id):
    return redirect("/dashboard")

# =========================================================
# INDEX
# =========================================================

@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conversations = db.execute(
        """
        SELECT * FROM conversations
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    latest_conversation = db.execute(
        """
        SELECT * FROM conversations
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (session["user_id"],)
    ).fetchone()

    messages = []
    mod = "—"

    if latest_conversation is not None:
        messages = db.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (latest_conversation["id"],)
        ).fetchall()
        mod = latest_conversation["mode"] if latest_conversation["mode"] else "—"

    current_user = SimpleNamespace(name=user["username"] if user else "Teacher")

    return render_template(
        "index.html",
        user=user,
        current_user=current_user,
        conversations=conversations,
        messages=messages,
        mod=mod,
        recent_conversations=conversations,
        recent_materials=[],
        active_conversations_count=len(conversations),
        generated_materials_count=0,
        weekly_activity_count=0,
    )

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
    return redirect("/landing")
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
        prompt = request.form.get("prompt")
        if prompt and prompt.strip():
            # Save user prompt
            db.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, "user", prompt)
            )
            connect.commit()

            # Resolve image path
            image_filename = f"mode4_{conversation_id}.png"
            image_path = os.path.join("uploads", image_filename)
            if not os.path.exists(image_path):
                image_filename = f"mode4_{conversation_id}.jpg"
                image_path = os.path.join("uploads", image_filename)
            if not os.path.exists(image_path):
                image_path = "static/userpic.png"

            # Build history for context
            history_rows = db.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
                (conversation_id,)
            ).fetchall()
            history = "\n".join([f"{row['role']}: {row['content']}" for row in history_rows])

            response = ai.handwriting(prompt, history, image_path=image_path)

            # Save assistant response
            db.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, "assistant", response)
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

@app.route("/mode4/upload/<int:conversation_id>", methods=["POST"])
@login_required
def mode4_upload(conversation_id):
    conversation = db.execute(
        """
        SELECT * FROM conversations WHERE id = ? AND user_id = ? AND mode = ?
        """,
        (conversation_id, session["user_id"], "mode4")
    ).fetchone()

    if not conversation:
        return apology("conversație inexistentă", 404)

    file = request.files.get("file")
    if file and file.filename:
        os.makedirs("uploads", exist_ok=True)
        _, ext = os.path.splitext(file.filename)
        if not ext:
            ext = ".png"
        filename = f"mode4_{conversation_id}{ext}"
        filepath = os.path.join("uploads", filename)
        file.save(filepath)

        initial_prompt = "Te rog să transcrii această imagine/PDF de exerciții matematice scrise de mână."
        
        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "user", f"Fișier încărcat: <i>{file.filename}</i>")
        )
        connect.commit()

        response = ai.handwriting(initial_prompt, "", image_path=filepath)

        db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "assistant", response)
        )
        connect.commit()

        if conversation["title"] == "Conversație nouă":
            db.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (f"Transcriere {file.filename[:20]}", conversation_id)
            )
            connect.commit()

    return redirect(f"/mode4/{conversation_id}")
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
# RUN (Reloaded to refresh translations JSON keys)
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)
