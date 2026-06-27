from flask import render_template, request, session, redirect
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
import uuid
import app
from werkzeug.utils import secure_filename

def style_function(apology, db, connect):
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

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

        db.execute(
            """
            INSERT INTO styles
            (user_id, style_name, test_type, style_description, documents)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                style_name,
                test_type,
                style_description,
                files_string
            )
        )
        connect.commit()

        return redirect("/menu")

    return render_template("style.html", user=user)

def login_function(db, apology):
    lang = session.get("lang", "ro")
    session.clear()
    session["lang"] = lang

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        # =========================
        # VALIDATION
        # =========================

        if not email:
            return apology(app.t("err_must_provide_email"), 400)

        if not password:
            return apology(app.t("err_must_provide_password"), 400)

        # =========================
        # FIND USER
        # =========================

        rows = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchall()

        # =========================
        # CHECK USER
        # =========================

        if len(rows) != 1:

            return apology(
                app.t("err_invalid_credentials"),
                400
            )

        user = rows[0]

        # =========================
        # CHECK PASSWORD
        # =========================

        if not check_password_hash(
            user["hash"],
            password
        ):

            return apology(
                app.t("err_invalid_credentials"),
                400
            )

        # =========================
        # LOGIN USER
        # =========================

        session["user_id"] = user["id"]
        session["gender"] = user["gender"]

        # login -> menu
        return redirect("/menu")

    return render_template("login.html")

def register_function(db, connect, apology):
    lang = session.get("lang", "ro")
    session.clear()
    session["lang"] = lang

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
            return apology(app.t("err_must_provide_email"), 400)

        if not password:
            return apology(app.t("err_must_provide_password"), 400)

        if not username:
            return apology(app.t("err_must_provide_username"), 400)

        if not gender:
            return apology(app.t("err_must_provide_gender"), 400)

        if not tehnologie:
            return apology(app.t("err_must_provide_tech"), 400)

        if not liceu:
            return apology(app.t("err_must_provide_highschool"), 400)

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

            db.execute(
                """
                INSERT INTO users
                (email, hash, username, gender, tehnologie, liceu)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    email,
                    hash_password,
                    username,
                    gender,
                    tehnologie,
                    liceu
                )
            )

            connect.commit()

            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            session["user_id"] = user_id
            session["gender"] = gender

            # dupa register -> style
            return redirect("/style")

        except sqlite3.IntegrityError:

            return apology(
                app.t("err_user_exists"),
                400
            )

    return render_template("register.html")

def account_function(db):
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    return render_template(
        "account.html",
        username=user["username"],
        email=user["email"]
    )

def password_function(db, connect, apology):
    if request.method == "POST":

        password = request.form.get("password")

        if not password:

            return apology(
                "must provide password",
                400
            )

        hash_password = generate_password_hash(
            password,
            method="scrypt",
            salt_length=16
        )

        db.execute(
            "UPDATE users SET hash = ? WHERE id = ?",
            (
                hash_password,
                session["user_id"]
            )
        )

        connect.commit()

        return redirect("/account")

    return render_template("account.html")
