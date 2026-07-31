from functools import wraps
import json
import os
from types import SimpleNamespace
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash
#import markdown
#mode3
from PyPDF2 import PdfReader
from docx import Document
from secondary import ai, docs, ocr, accounts
from secondary import model_route
from secondary.document_editor import document_editor_bp
from bac_generator.routes import bac_generator_bp
from bac_generator.generator import BACExamGenerator
from models import SessionLocal, User, Conversation, Message, Style, init_db
import traceback

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "dev-only-insecure-secret-key"
app.register_blueprint(bac_generator_bp)
app.register_blueprint(document_editor_bp)
os.makedirs("uploads", exist_ok=True)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['TEMPLATES_AUTO_RELOAD'] = True


Session(app)


@app.teardown_appcontext
def remove_db_session(exception=None):
    SessionLocal.remove()

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
init_db()

# scoped_session, so every request/thread transparently gets its own
# SQLAlchemy Session; teardown_appcontext above releases it after each request.
db = SessionLocal

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

@app.route("/health")
def health():
    return jsonify(status="ok"), 200

# =========================================================
# INDEX
# =========================================================

@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user = db.get(User, session["user_id"])

    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"])
        .order_by(Conversation.created_at.desc())
    ).all()

    latest_conversation = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"])
        .order_by(Conversation.created_at.desc())
        .limit(1)
    ).first()

    messages = []
    mod = "—"

    if latest_conversation is not None:
        messages = db.scalars(
            select(Message)
            .where(Message.conversation_id == latest_conversation.id)
            .order_by(Message.id.asc())
        ).all()
        mod = latest_conversation.mode if latest_conversation.mode else "—"

    current_user = SimpleNamespace(name=user.username if user else "Teacher")

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
    return accounts.register_function(db, apology)
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
    return accounts.password_function(db, apology)
# =========================================================
# STYLE
# =========================================================
@app.route("/style", methods=["GET", "POST"])
@login_required
def style():
    return accounts.style_function(apology, db)
    #TODO
# =========================================================
# MENU
# =========================================================
@app.route("/menu")
@login_required
def menu():

    styles = db.scalars(
        select(Style).where(Style.user_id == session["user_id"]).order_by(Style.id.desc())
    ).all()

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

    conversation = Conversation(user_id=session["user_id"], mode="mode1", title="Conversație nouă")
    db.add(conversation)
    db.commit()
    conversation_id = conversation.id
    return redirect(f"/mode1/{conversation_id}")


@app.route("/mode1/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode1(conversation_id):
    return model_route.mode1_chat(db, apology, conversation_id)

# =========================================================
# MODE2
# =========================================================
# =========================================================
# MODE2
# =========================================================
@app.route("/create_mode2", methods=["POST"])
@login_required
def create_mode2():

    raw_style_id = request.form.get("style")
    try:
        style_id = int(raw_style_id) if raw_style_id else None
    except (TypeError, ValueError):
        style_id = None
    school_class = request.form.get("school_class")
    bac = request.form.get("bac")

    conversation = Conversation(
        user_id=session["user_id"],
        mode="mode2",
        title="Traducere nouă",
        style_id=style_id,
        school_class=school_class,
        bac=bac,
    )
    db.add(conversation)
    db.commit()

    conversation_id = conversation.id
    return redirect(f"/mode2/{conversation_id}")


@app.route("/mode2/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode2(conversation_id):
    return model_route.mode2_chat(db, apology, conversation_id)

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

    conversation = Conversation(user_id=session["user_id"], mode="mode3", title=filename)
    db.add(conversation)
    db.commit()

    conversation_id = conversation.id

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
    return model_route.mode3_chat(db, apology, conversation_id, file_read, "uploads")
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
@app.route("/create_mode4", methods=["POST"])
@login_required
def create_mode4():

    uploaded_file = request.files.get("file")

    if not uploaded_file or uploaded_file.filename == "":
        return apology("Nicio poză sau fișier încărcat", 400)

    if not allowed_file(uploaded_file.filename):
        return apology("Tip de fișier nepermis", 400)

    filename = secure_filename(uploaded_file.filename)
    os.makedirs("uploads", exist_ok=True)
    uploaded_file.save(f"uploads/{filename}")

    conversation = Conversation(user_id=session["user_id"], mode="mode4", title=filename)
    db.add(conversation)
    db.commit()

    conversation_id = conversation.id

    return redirect(f"/mode4/{conversation_id}")


@app.route("/mode4")
@login_required
def mode4_latest():
    conversation = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == "mode4")
        .order_by(Conversation.created_at.desc())
        .limit(1)
    ).first()

    if not conversation:
        return redirect("/menu")

    return redirect(f"/mode4/{conversation.id}")


@app.route("/mode4/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode4(conversation_id):
    return model_route.mode4_chat(db, apology, conversation_id, "uploads")
# =========================================================
# MODE5
# =========================================================
#TODO
@app.route("/create_mode5", methods=["GET", "POST"])
@login_required
def create_mode5():

    conversation = Conversation(user_id=session["user_id"], mode="mode5", title="Varianta BAC nouă")
    db.add(conversation)
    db.commit()

    conversation_id = conversation.id

    # Generate the first BAC variant right away so the user doesn't land on an empty chat
    default_lessons = [
        "Radicali", "Puteri", "Progresii", "Probabilități",
        "Funcții", "Logaritmi", "Numere complexe", "Trigonometrie",
        "Matrici", "Legi de compoziție", "Limite", "Derivate",
        "Integrale definite", "Polinoame",
    ]
    generator = BACExamGenerator()
    exam_data = generator.generate_exam(default_lessons)

    db.add(Message(
        conversation_id=conversation_id,
        role="assistant",
        content=exam_data["html_preview"],
        exam_data=json.dumps(exam_data),
    ))
    db.commit()

    return redirect(f"/mode5/{conversation_id}")

@app.route("/mode5")
@login_required
def mode5_latest():
    conversation = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == "mode5")
        .order_by(Conversation.created_at.desc())
        .limit(1)
    ).first()

    if not conversation:
        return redirect("/menu")

    return redirect(f"/mode5/{conversation.id}")


@app.route("/mode5/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def mode5(conversation_id):
    conversation = db.scalars(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == session["user_id"],
            Conversation.mode == "mode5",
        )
    ).first()

    if not conversation:
        return apology("conversație inexistentă", 404)

    if request.method == "POST":
        prompt = request.form.get("prompt")
        if prompt and prompt.strip():
            db.add(Message(conversation_id=conversation_id, role="user", content=prompt))
            db.commit()

    raw_messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
    ).all()

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

    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == "mode5")
        .order_by(Conversation.created_at.desc())
    ).all()

    return render_template(
        "modes/mode5.html",
        messages=messages,
        conversations=conversations,
        conversation=conversation,
        conversation_id=conversation_id,
        bac=conversation.bac
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

    conversation = db.scalars(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == session["user_id"])
    ).first()

    if not conversation:
        return apology("Conversație inexistentă.", 404)

    conversation.title = new_title
    db.commit()

    return redirect(f"/{conversation.mode}/{conversation_id}")


@app.route("/conversation/<int:conversation_id>/delete", methods=["POST"])
@login_required
def delete_conversation(conversation_id):
    conversation = db.scalars(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == session["user_id"])
    ).first()

    if not conversation:
        return apology("Conversație inexistentă.", 404)

    mode = conversation.mode

    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()

    next_conversation = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == session["user_id"], Conversation.mode == mode)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    ).first()

    if next_conversation:
        return redirect(f"/{mode}/{next_conversation.id}")

    return redirect("/menu")
# =========================================================
# RUN (Reloaded to refresh translations JSON keys)
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)
