from flask import render_template, request, session, redirect
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import os
import uuid
import app
from werkzeug.utils import secure_filename
from models import Style, User, Conversation

def style_function(apology, db):
    user = db.get(User, session["user_id"])

    if request.method == "POST":

        test_type = request.form.get("test_type")
        style_description = request.form.get("style_description")
        style_name = request.form.get("style_name")

        if not style_name:
            return apology("adauga numele stilului", 400)
        if not test_type:
            return apology("selecteaza tipul", 400)

        if not style_description:
            return apology("adauga descriere", 400)

        uploaded_files = request.files.getlist("documents")

        saved_files = []
        os.makedirs("static/uploads/styles", exist_ok=True)

        for file in uploaded_files:

            # skip daca nu exista fisier
            if not file or file.filename == "":
                continue

            # verifica extensia
            if not app.allowed_file(file.filename):
                return apology("fisier invalid (png, jpg, jpeg, pdf, docx)", 400)

            # nume securizat
            safe_name = secure_filename(file.filename)

            # nume unic
            filename = (
                f"{session['user_id']}_"
                f"{uuid.uuid4()}_"
                f"{safe_name}"
            )

            filepath = os.path.join("static/uploads/styles", filename)

            # salveaza fisier
            file.save(filepath)

            saved_files.append(filepath)

        files_string = ",".join(saved_files)

        db.add(Style(
            user_id=session["user_id"],
            style_name=style_name,
            test_type=test_type,
            style_description=style_description,
            documents=files_string,
        ))
        db.commit()

        return redirect("/menu")

    return render_template("style.html", user=user)

def login_function(db, apology):
    session.clear()

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        # =========================
        # VALIDATION
        # =========================

        if not email:
            return apology("must provide email", 400)

        if not password:
            return apology("must provide password", 400)

        # =========================
        # FIND USER
        # =========================

        rows = db.scalars(
            select(User).where(User.email == email)
        ).all()

        # =========================
        # CHECK USER
        # =========================

        if len(rows) != 1:

            return apology(
                "invalid email and/or password",
                400
            )

        user = rows[0]

        # =========================
        # CHECK PASSWORD
        # =========================

        if not check_password_hash(
            user.hash,
            password
        ):

            return apology(
                "invalid email and/or password",
                400
            )

        # =========================
        # LOGIN USER
        # =========================

        session["user_id"] = user.id
        session["gender"] = user.gender

        # login -> dashboard
        return redirect("/dashboard")

    return render_template("login.html")

def register_function(db, apology):
    session.clear()

    if request.method == "POST":

        # =========================
        # GET DATA
        # =========================

        email = request.form.get("email")
        password = request.form.get("password")
        username = request.form.get("username")
        gender = request.form.get("gender")
        tehnologie = request.form.get("tehnologie")
        liceu = request.form.get("liceu")

        # =========================
        # VALIDATION
        # =========================

        if not email:
            return apology("must provide email", 400)

        if not password:
            return apology("must provide password", 400)

        if not username:
            return apology("must provide username", 400)

        if not gender:
            return apology("must provide gender", 400)

        if not tehnologie:
            return apology("must provide tehnologie", 400)

        if not liceu:
            return apology("must provide liceu", 400)

        # =========================
        # HASH PASSWORD
        # =========================

        hash_password = generate_password_hash(
            password,
            method="scrypt",
            salt_length=16
        )

        # =========================
        # INSERT USER
        # =========================

        try:

            user = User(
                email=email,
                hash=hash_password,
                username=username,
                gender=gender,
                tehnologie=tehnologie,
                liceu=liceu,
            )
            db.add(user)
            db.commit()

            session["user_id"] = user.id
            session["gender"] = gender

            # dupa register -> ghid website (mode1)
            conversation = Conversation(user_id=user.id, mode="mode1", title="Ghid Website")
            db.add(conversation)
            db.commit()

            return redirect(f"/mode1/{conversation.id}")

        except IntegrityError:

            db.rollback()

            return apology(
                "user already registered",
                400
            )

    return render_template("register.html")

def account_function(db):
    user = db.get(User, session["user_id"])

    return render_template(
        "account.html",
        username=user.username,
        email=user.email
    )

def password_function(db, apology):
    if request.method == "POST":

        current_password = request.form.get("current_password")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not current_password:
            return apology("trebuie să introduci parola curentă", 400)

        if not password:
            return apology("trebuie să introduci parola nouă", 400)

        if not confirmation:
            return apology("trebuie să confirmi parola nouă", 400)

        if password != confirmation:
            return apology("parolele nu coincid", 400)

        # verify current password
        user = db.get(User, session["user_id"])

        if not user or not check_password_hash(user.hash, current_password):
            return apology("parola curentă este incorectă", 400)

        # update password
        hash_password = generate_password_hash(
            password,
            method="scrypt",
            salt_length=16
        )

        user.hash = hash_password
        db.commit()

        return redirect("/account")

    return render_template("passwordchange.html")