import json
import os
import markdown
from collections import Counter
from datetime import datetime
from flask import render_template, request, session, redirect, jsonify
from sqlalchemy import delete, select
from werkzeug.utils import secure_filename
from secondary import ai
from models import (
    AiInsight,
    ChatMessage,
    Class,
    Group,
    GroupMember,
    Metric,
    Profile,
    Student,
    Style,
    TestRecord,
)

# =========================================================
# "ELEVII MEI" — classroom platform
# Student risk overview, AI profile/insights, exercise
# generator (reuses secondary.ai.assistant), smart groups.
#
# URL layout:
#   /elevi[/<id>]                My Students — risk overview
#   /elevi/<id>/nou               full add-student profiling form
#   /elevi/<id>/<sid>              student page (4 modes via ?tab=)
#   /elevi/<id>/grupe             Smart Groups board
#   /elevi/<id>/grupa/<gid>        group detail (suggested actions + group exercises)
# =========================================================

RISK_LEVELS = {"Ridicat", "Mediu", "Scăzut"}
TREND_ICONS = {"up": "↑", "down": "↓", "stable": "→"}
ALLOWED_UPLOAD_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


def _allowed_upload(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def _save_upload(file_storage, upload_folder="uploads"):
    if not file_storage or not file_storage.filename or not _allowed_upload(file_storage.filename):
        return None
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
    file_storage.save(os.path.join(upload_folder, unique_name))
    return unique_name


def _infer_profile_extras(risk, confidence):
    """Sensible defaults for the new profiling fields, used only for seed
    students that don't have hand-written narratives (Maria/Alex do)."""
    if risk == "Ridicat":
        return ("Retras, pierde ușor încrederea după greșeli repetate",
                 "Scurtă (10-15 min), scade rapid după eșecuri",
                 "2-3 lecții recente (recuperare necesară)")
    if risk == "Mediu":
        return ("Cooperant, dar ocazional neatent la detalii",
                 "Medie (20-25 min)",
                 "1 lecție recentă")
    return ("Încrezător, motivat, participă activ",
             "Lungă (35+ min)",
             "Fără absențe recente")


# ---------------------------------------------------------
# Seed data (demo content, created once per teacher account)
# ---------------------------------------------------------

def _generic_insight(name, weakness, confidence):
    why = (
        f"{name} întâmpină dificultăți repetate la capitolul {weakness.lower()}. "
        f"Rezultatele arată o înțelegere parțială a conceptelor de bază, iar nivelul de încredere "
        f"({confidence.lower()}) scade atunci când exercițiile cresc în dificultate."
    )
    actions = [
        {"text": f"Recapitulează noțiunile fundamentale de {weakness.lower()} înainte de a continua", "done": False},
        {"text": f"Atribuie exerciții suplimentare de {weakness.lower()} cu dificultate progresivă", "done": False},
        {"text": "Verifică progresul după fiecare set de exerciții rezolvate", "done": False},
    ]
    return why, actions


def _generate_group_description(weakness_tag):
    # TODO: replace with real AI call — currently a templated 2-line
    # placeholder keyed by the group's shared weakness, same mock boundary
    # as _default_group_actions() below.
    descriptions = {
        "fractii": (
            "Acest grup reunește elevi cu dificultăți similare la operațiile cu fracții și la simplificare. "
            "Recomandăm exemple vizuale repetate și pași intermediari explicați clar."
        ),
        "functii": (
            "Elevii din această grupă au nevoie de mai multă practică la reprezentarea și interpretarea funcțiilor. "
            "Abordările grafice și exemplele aplicate pot accelera progresul comun."
        ),
        "avansat": (
            "Grup de elevi cu rezultate constante, pregătiți pentru exerciții de dificultate crescută. "
            "Pot prelua provocări suplimentare și materiale de aprofundare."
        ),
    }
    return descriptions.get(
        weakness_tag,
        "Grup format din elevi cu un profil de dificultăți asemănător. "
        "Recomandăm o primă sesiune comună pentru a calibra abordarea potrivită.",
    )


# ---------------------------------------------------------
# Small query helpers. `db` is the app's scoped SQLAlchemy
# session (app.db), so every function here commits through it
# instead of the raw sqlite connection this feature was
# originally prototyped against.
# ---------------------------------------------------------

def _teacher_classes(db, teacher_id):
    return db.scalars(
        select(Class).where(Class.teacher_id == teacher_id).order_by(Class.id.asc())
    ).all()


def _owned_class(db, teacher_id, class_id):
    if not class_id:
        return None
    return db.scalars(
        select(Class).where(Class.id == class_id, Class.teacher_id == teacher_id)
    ).first()


def _student_in_class(db, sid, class_id):
    return db.scalars(
        select(Student).where(Student.id == sid, Student.class_id == class_id)
    ).first()


def _seed_class(db, teacher_id, class_name, students):
    school_class = Class(name=class_name, teacher_id=teacher_id)
    db.add(school_class)
    db.flush()

    groups = {}
    for tag, name in (
        ("fractii", "Grupa A — Fracții"),
        ("functii", "Grupa B — Funcții"),
        ("avansat", "Grupa C — Pregătiți pentru avansat"),
    ):
        group = Group(
            class_id=school_class.id,
            name=name,
            weakness_tag=tag,
            description=_generate_group_description(tag),
        )
        db.add(group)
        db.flush()
        groups[tag] = group.id

    for s in students:
        student = Student(class_id=school_class.id, name=s["name"])
        db.add(student)
        db.flush()
        sid = student.id

        db.add(Metric(
            student_id=sid,
            attendance=s["attendance"],
            avg_grade=s["avg_grade"],
            mastery_pct=s["mastery"],
            completion_pct=s["completion"],
            avg_time_per_ex=s["avg_time"],
            repeated_mistakes=s["mistakes"],
            risk_level=s["risk"],
            risk_trend=s["trend"],
        ))

        personality, attention, absent = s.get("personality"), s.get("attention_span"), s.get("absent_lessons")
        if personality is None:
            personality, attention, absent = _infer_profile_extras(s["risk"], s["confidence"])

        db.add(Profile(
            student_id=sid,
            strengths=s["strengths"],
            weaknesses=s["weaknesses"],
            learning_style=s["learning_style"],
            confidence=s["confidence"],
            risk_level=s["risk"],
            personality_traits=personality,
            attention_span=attention,
            absent_lessons=absent,
        ))

        if "why" in s:
            why, actions = s["why"], s["actions"]
        else:
            why, actions = _generic_insight(s["name"], s["weaknesses"].split(",")[0].strip(), s["confidence"])

        db.add(AiInsight(
            student_id=sid,
            why_struggling=why,
            recommended_actions_json=json.dumps(actions, ensure_ascii=False),
        ))

        primary_weakness = s["weaknesses"].lower()
        if "fracți" in primary_weakness:
            group_key = "fractii"
        elif "func" in primary_weakness:
            group_key = "functii"
        elif s["risk"] == "Scăzut":
            group_key = "avansat"
        else:
            group_key = "functii"

        db.add(GroupMember(group_id=groups[group_key], student_id=sid))

    db.commit()


def _seed_if_needed(db, teacher_id):
    existing = db.scalars(
        select(Class.id).where(Class.teacher_id == teacher_id).limit(1)
    ).first()

    if existing:
        return

    maria_why = (
        "Maria confundă frecvent regulile de simplificare a fracțiilor și pierde încrederea "
        "atunci când exercițiile devin abstracte. Înțelege conceptele atunci când sunt "
        "prezentate vizual, dar are nevoie de exemple repetate înainte de a lucra independent."
    )
    maria_actions = [
        {"text": "Recapitulează operațiile cu fracții cu exemple vizuale înainte de ecuații", "done": False},
        {"text": "Oferă exerciții mai scurte, cu mai multe repetiții", "done": False},
        {"text": "Folosește diagrame pentru a introduce ecuațiile liniare", "done": False},
        {"text": "Verifică încrederea după fiecare 2-3 exerciții rezolvate", "done": False},
    ]

    alex_why = (
        "Alex face frecvent erori de semn atunci când rezolvă ecuații. Înțelege metoda de "
        "rezolvare, dar are dificultăți la manipularea algebrică. Încrederea scade vizibil "
        "după greșeli consecutive."
    )
    alex_actions = [
        {"text": "Petrece 5 minute recapitulând regulile de semn înainte de material nou", "done": False},
        {"text": "Atribuie o fișă de simplificare algebrică", "done": False},
        {"text": "Plasează-l în Grupa de Sprijin — Ecuații Liniare", "done": False},
        {"text": "Amână ecuațiile de gradul 2 până la atingerea pragului de stăpânire", "done": False},
    ]

    _seed_class(db, teacher_id, "Clasa IX A", [
        {"name": "Maria Popescu", "attendance": 78, "avg_grade": 5.8, "mastery": 42, "completion": 55,
         "avg_time": "9 min/ex", "mistakes": 14, "risk": "Ridicat", "trend": "down",
         "strengths": "Geometrie, Raționament vizual", "weaknesses": "Algebră, Fracții, Ecuații",
         "learning_style": "Exemple vizuale, exerciții scurte, repetiție frecventă", "confidence": "Scăzută",
         "personality": "Emotivă, sensibilă la eșecuri repetate, are nevoie de încurajare constantă",
         "attention_span": "Scurtă (10-15 min), scade vizibil după greșeli",
         "absent_lessons": "Ecuații de gradul 2 (12.03), Progresii (19.03)",
         "why": maria_why, "actions": maria_actions},
        {"name": "Bogdan Ionescu", "attendance": 91, "avg_grade": 7.6, "mastery": 68, "completion": 82,
         "avg_time": "5 min/ex", "mistakes": 5, "risk": "Mediu", "trend": "stable",
         "strengths": "Algebră", "weaknesses": "Trigonometrie",
         "learning_style": "Explicații pas cu pas", "confidence": "Medie"},
        {"name": "Elena Radu", "attendance": 96, "avg_grade": 8.9, "mastery": 88, "completion": 95,
         "avg_time": "3 min/ex", "mistakes": 1, "risk": "Scăzut", "trend": "up",
         "strengths": "Funcții, Geometrie", "weaknesses": "Progresii",
         "learning_style": "Exerciții de aprofundare, provocări suplimentare", "confidence": "Ridicată"},
        {"name": "Andrei Dumitrescu", "attendance": 82, "avg_grade": 6.1, "mastery": 49, "completion": 60,
         "avg_time": "8 min/ex", "mistakes": 12, "risk": "Mediu", "trend": "down",
         "strengths": "Geometrie", "weaknesses": "Fracții, Ecuații",
         "learning_style": "Exemple vizuale, pași intermediari notați", "confidence": "Scăzută"},
        {"name": "Ioana Constantin", "attendance": 94, "avg_grade": 8.1, "mastery": 79, "completion": 88,
         "avg_time": "4 min/ex", "mistakes": 3, "risk": "Scăzut", "trend": "stable",
         "strengths": "Trigonometrie", "weaknesses": "Logaritmi",
         "learning_style": "Exerciții variate, ritm propriu", "confidence": "Ridicată"},
    ])

    _seed_class(db, teacher_id, "Clasa X A", [
        {"name": "Alex Marinescu", "attendance": 85, "avg_grade": 6.4, "mastery": 51, "completion": 68,
         "avg_time": "7 min/ex", "mistakes": 11, "risk": "Ridicat", "trend": "down",
         "strengths": "Recunoaște rapid metoda de rezolvare", "weaknesses": "Ecuații, Manipulare algebrică",
         "learning_style": "Explicații pas cu pas, feedback imediat după fiecare exercițiu", "confidence": "Medie",
         "personality": "Perseverent, dar se descurajează vizibil după erori consecutive",
         "attention_span": "Medie (20 min), bună la început, scade spre finalul orei",
         "absent_lessons": "Sisteme de ecuații (05.03)",
         "why": alex_why, "actions": alex_actions},
        {"name": "Diana Stanciu", "attendance": 93, "avg_grade": 8.3, "mastery": 81, "completion": 90,
         "avg_time": "4 min/ex", "mistakes": 2, "risk": "Scăzut", "trend": "up",
         "strengths": "Algebră, Funcții", "weaknesses": "Probabilități",
         "learning_style": "Studii de caz, exemple din viața reală", "confidence": "Ridicată"},
        {"name": "Mihai Popa", "attendance": 88, "avg_grade": 7.0, "mastery": 63, "completion": 74,
         "avg_time": "6 min/ex", "mistakes": 7, "risk": "Mediu", "trend": "stable",
         "strengths": "Ecuații", "weaknesses": "Funcții",
         "learning_style": "Grafice și reprezentări vizuale", "confidence": "Medie"},
        {"name": "Cristina Neagu", "attendance": 74, "avg_grade": 5.4, "mastery": 38, "completion": 50,
         "avg_time": "10 min/ex", "mistakes": 16, "risk": "Ridicat", "trend": "down",
         "strengths": "Perseverență", "weaknesses": "Fracții, Algebră",
         "learning_style": "Exerciții scurte, repetiție frecventă, încurajare constantă", "confidence": "Scăzută"},
        {"name": "Vlad Toma", "attendance": 90, "avg_grade": 7.8, "mastery": 72, "completion": 85,
         "avg_time": "5 min/ex", "mistakes": 4, "risk": "Scăzut", "trend": "up",
         "strengths": "Algebră, Funcții", "weaknesses": "Geometrie",
         "learning_style": "Construcții geometrice pas cu pas", "confidence": "Ridicată"},
    ])

    _seed_class(db, teacher_id, "Clasa XI A", [
        {"name": "Ana Barbu", "attendance": 87, "avg_grade": 7.2, "mastery": 65, "completion": 77,
         "avg_time": "6 min/ex", "mistakes": 8, "risk": "Mediu", "trend": "stable",
         "strengths": "Funcții", "weaknesses": "Derivate",
         "learning_style": "Exemple rezolvate complet înainte de exerciții individuale", "confidence": "Medie"},
        {"name": "Robert Șerban", "attendance": 95, "avg_grade": 8.6, "mastery": 84, "completion": 92,
         "avg_time": "4 min/ex", "mistakes": 2, "risk": "Scăzut", "trend": "up",
         "strengths": "Algebră, Logică", "weaknesses": "Matrici",
         "learning_style": "Exerciții de dificultate crescută, ritm rapid", "confidence": "Ridicată"},
        {"name": "Simona Voicu", "attendance": 71, "avg_grade": 5.1, "mastery": 35, "completion": 47,
         "avg_time": "11 min/ex", "mistakes": 17, "risk": "Ridicat", "trend": "down",
         "strengths": "Geometrie", "weaknesses": "Limite, Derivate",
         "learning_style": "Explicații foarte detaliate, un concept nou pe sesiune", "confidence": "Scăzută"},
        {"name": "George Petrescu", "attendance": 89, "avg_grade": 7.4, "mastery": 66, "completion": 79,
         "avg_time": "6 min/ex", "mistakes": 7, "risk": "Mediu", "trend": "stable",
         "strengths": "Trigonometrie", "weaknesses": "Progresii",
         "learning_style": "Exerciții structurate pe pași", "confidence": "Medie"},
        {"name": "Larisa Manea", "attendance": 93, "avg_grade": 8.2, "mastery": 78, "completion": 87,
         "avg_time": "4 min/ex", "mistakes": 3, "risk": "Scăzut", "trend": "stable",
         "strengths": "Algebră, Funcții", "weaknesses": "Numere complexe",
         "learning_style": "Exerciții variate, aplicații practice", "confidence": "Ridicată"},
    ])

    _seed_class(db, teacher_id, "Clasa XII A", [
        {"name": "Cătălin Iancu", "attendance": 84, "avg_grade": 6.7, "mastery": 55, "completion": 70,
         "avg_time": "7 min/ex", "mistakes": 10, "risk": "Mediu", "trend": "down",
         "strengths": "Derivate", "weaknesses": "Integrale",
         "learning_style": "Recapitulare frecventă a formulelor de bază", "confidence": "Medie"},
        {"name": "Alexandra Grigore", "attendance": 95, "avg_grade": 8.8, "mastery": 86, "completion": 93,
         "avg_time": "3 min/ex", "mistakes": 1, "risk": "Scăzut", "trend": "up",
         "strengths": "Integrale, Logică", "weaknesses": "Probabilități",
         "learning_style": "Probleme complexe, competiții matematice", "confidence": "Ridicată"},
        {"name": "Daniel Nistor", "attendance": 69, "avg_grade": 4.9, "mastery": 31, "completion": 44,
         "avg_time": "12 min/ex", "mistakes": 19, "risk": "Ridicat", "trend": "down",
         "strengths": "Perseverență", "weaknesses": "Integrale, Derivate",
         "learning_style": "Exemple video, exerciții foarte ghidate", "confidence": "Scăzută"},
        {"name": "Roxana Enache", "attendance": 90, "avg_grade": 7.5, "mastery": 69, "completion": 80,
         "avg_time": "5 min/ex", "mistakes": 6, "risk": "Mediu", "trend": "stable",
         "strengths": "Logaritmi", "weaknesses": "Ecuații exponențiale",
         "learning_style": "Exerciții progresive de dificultate", "confidence": "Medie"},
        {"name": "Ștefan Cojocaru", "attendance": 92, "avg_grade": 8.0, "mastery": 75, "completion": 86,
         "avg_time": "4 min/ex", "mistakes": 3, "risk": "Scăzut", "trend": "up",
         "strengths": "Derivate, Integrale", "weaknesses": "Logaritmi",
         "learning_style": "Exerciții variate, ritm propriu", "confidence": "Ridicată"},
    ])


# ---------------------------------------------------------
# Shared: resolve teacher's classes + a risk-sorted roster
# with aggregate stats for the selected class. Used by both
# the Main Dashboard and the My Students page.
# ---------------------------------------------------------

def _risk_overview_data(db, teacher_id, class_id):
    classes = _teacher_classes(db, teacher_id)

    if not classes:
        return classes, None, [], {}

    selected_class = None
    if class_id:
        selected_class = next((c for c in classes if c.id == class_id), None)
    if not selected_class:
        selected_class = classes[0]

    sort = request.args.get("sort", "risk")

    rows = db.execute(
        select(
            Student.id, Student.name, Metric.attendance, Metric.avg_grade,
            Metric.mastery_pct, Metric.completion_pct, Metric.avg_time_per_ex,
            Metric.repeated_mistakes, Metric.risk_level, Metric.risk_trend,
        )
        .join(Metric, Metric.student_id == Student.id)
        .where(Student.class_id == selected_class.id)
    ).mappings().all()

    risk_order = {"Ridicat": 0, "Mediu": 1, "Scăzut": 2}
    sort_keys = {
        "name": lambda r: r["name"],
        "attendance": lambda r: -(r["attendance"] or 0),
        "avg_grade": lambda r: -(r["avg_grade"] or 0),
        "mastery_pct": lambda r: -(r["mastery_pct"] or 0),
        "completion_pct": lambda r: -(r["completion_pct"] or 0),
        "repeated_mistakes": lambda r: -(r["repeated_mistakes"] or 0),
        "risk": lambda r: risk_order.get(r["risk_level"], 3),
    }
    key_fn = sort_keys.get(sort, sort_keys["risk"])
    students = sorted([dict(r) for r in rows], key=key_fn)

    total_students = len(students)
    avg_attendance = round(sum(s["attendance"] or 0 for s in students) / total_students, 1) if total_students else 0
    avg_mastery = round(sum(s["mastery_pct"] or 0 for s in students) / total_students, 1) if total_students else 0
    avg_completion = round(sum(s["completion_pct"] or 0 for s in students) / total_students, 1) if total_students else 0

    risk_counts = {"Ridicat": 0, "Mediu": 0, "Scăzut": 0}
    trend_counts = {"up": 0, "down": 0, "stable": 0}
    for s in students:
        risk_counts[s["risk_level"]] = risk_counts.get(s["risk_level"], 0) + 1
        trend_counts[s["risk_trend"]] = trend_counts.get(s["risk_trend"], 0) + 1

    weakness_rows = db.scalars(
        select(Profile.weaknesses)
        .join(Student, Student.id == Profile.student_id)
        .where(Student.class_id == selected_class.id)
    ).all()
    weakness_counter = Counter()
    for weaknesses in weakness_rows:
        for tag in (weaknesses or "").split(","):
            tag = tag.strip()
            if tag and tag != "De evaluat":
                weakness_counter[tag] += 1
    top_weaknesses = weakness_counter.most_common(5)

    extra = {
        "sort": sort,
        "total_students": total_students,
        "avg_attendance": avg_attendance,
        "avg_mastery": avg_mastery,
        "avg_completion": avg_completion,
        "risk_counts": risk_counts,
        "trend_counts": trend_counts,
        "top_weaknesses": top_weaknesses,
    }
    return classes, selected_class, students, extra


# ---------------------------------------------------------
# My Students — the "Elevii mei" nav section landing page:
# class picker + risk-sorted roster.
# ---------------------------------------------------------

def elevi_page(db, class_id=None):
    teacher_id = session["user_id"]
    _seed_if_needed(db, teacher_id)

    classes, selected_class, students, extra = _risk_overview_data(db, teacher_id, class_id)
    if not classes:
        return render_template("clasa/elevi.html", classes=[], selected_class=None, students=[])

    return render_template("clasa/elevi.html", classes=classes, selected_class=selected_class,
                           students=students, **extra)


def create_class(db, apology):
    name = request.form.get("name", "").strip()
    if not name:
        return apology("Adaugă un nume pentru clasă", 400)

    school_class = Class(name=name, teacher_id=session["user_id"])
    db.add(school_class)
    db.commit()

    return redirect(f"/elevi/{school_class.id}")


# ---------------------------------------------------------
# Add Student — full profiling form, filled out in one go.
# ---------------------------------------------------------

def add_student_form(db, apology, class_id):
    teacher_id = session["user_id"]
    classes = _teacher_classes(db, teacher_id)
    cls = next((c for c in classes if c.id == class_id), None)
    if not cls:
        return apology("Clasă inexistentă", 404)

    return render_template("clasa/elev_nou.html", classes=classes, selected_class=cls)


def add_student_submit(db, apology, class_id):
    teacher_id = session["user_id"]
    target_class_id = request.form.get("class_id", type=int) or class_id
    cls = _owned_class(db, teacher_id, target_class_id)
    if not cls:
        return apology("Clasă inexistentă", 404)

    name = request.form.get("name", "").strip()
    if not name:
        return apology("Adaugă numele elevului", 400)

    attendance = request.form.get("attendance", type=int) or 80
    absent_lessons = request.form.get("absent_lessons", "").strip() or "Fără absențe înregistrate"
    personality_traits = request.form.get("personality_traits", "").strip() or "De evaluat"
    attention_span = request.form.get("attention_span", "").strip() or "De evaluat"
    weaknesses_hint = request.form.get("weaknesses", "").strip()

    student = Student(class_id=target_class_id, name=name)
    db.add(student)
    db.flush()
    sid = student.id

    db.add(Metric(
        student_id=sid, attendance=attendance, avg_grade=6.0, mastery_pct=50,
        completion_pct=60, avg_time_per_ex="— min/ex", repeated_mistakes=0,
        risk_level="Mediu", risk_trend="stable",
    ))

    weaknesses = weaknesses_hint if weaknesses_hint else "De evaluat"
    db.add(Profile(
        student_id=sid, strengths="De evaluat", weaknesses=weaknesses,
        learning_style="De evaluat", confidence="Medie", risk_level="Mediu",
        personality_traits=personality_traits, attention_span=attention_span,
        absent_lessons=absent_lessons,
    ))

    # First test record, if the teacher filled in a grade/lessons pair or
    # uploaded the handwritten test + solution.
    grades = request.form.getlist("grades[]")
    lessons = request.form.getlist("lessons[]")
    test_filename = _save_upload(request.files.get("test_file"))
    solution_filename = _save_upload(request.files.get("solution_file"))

    first_grade = None
    first_lessons = None
    for g, l in zip(grades, lessons):
        if g.strip() or l.strip():
            first_grade = g.strip() or None
            first_lessons = l.strip() or None
            break

    if first_grade or first_lessons or test_filename or solution_filename:
        insights = _mock_test_insight(name, first_lessons, test_filename, solution_filename)
        db.add(TestRecord(
            student_id=sid, grade=_to_grade(first_grade), lessons=first_lessons,
            test_filename=test_filename, solution_filename=solution_filename,
            ai_insights=insights,
        ))

    # Generate the initial AI profile + insights in the same step, so the
    # student is added "fully in one go" instead of starting as a placeholder.
    why, actions = _build_profile_insight(name, weaknesses, personality_traits, attention_span,
                                          absent_lessons, attendance)
    db.add(AiInsight(
        student_id=sid, why_struggling=why,
        recommended_actions_json=json.dumps(actions, ensure_ascii=False),
    ))
    db.commit()

    return redirect(f"/elevi/{target_class_id}/{sid}")


def _to_grade(value):
    """`grade` is numeric in the schema but arrives as free text from the form."""
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _mock_test_insight(name, lessons, test_filename, solution_filename):
    # TODO: replace with real AI call — OCR the uploaded handwritten
    # solution against the given test and produce grounded insights instead
    # of this templated placeholder.
    if test_filename or solution_filename:
        return (
            f"Analiză automată a testului încărcat pentru {name}"
            + (f" ({lessons})" if lessons else "")
            + ". Fișa a fost salvată și este pregătită pentru recunoaștere OCR — "
            "conectează un model AI real pentru a extrage greșelile exacte și pentru a "
            "genera recomandări punctuale pe baza rezolvării scrise de mână."
        )
    return f"Rezultat înregistrat pentru {name}" + (f" la {lessons}" if lessons else "") + "."


def _build_profile_insight(name, weaknesses, personality_traits, attention_span, absent_lessons, attendance):
    # TODO: replace with real AI call — synthesize an actual profile from
    # the submitted grades/lessons/OCR results instead of templating one.
    primary_weakness = weaknesses.split(",")[0].strip() if weaknesses != "De evaluat" else "materie generală"
    why = (
        f"Profil inițial pentru {name}. Trăsături de personalitate observate: {personality_traits}. "
        f"Durata de concentrare estimată: {attention_span}. "
        f"Absențe/lecții recuperate: {absent_lessons}. Prezență: {attendance}%. "
        f"Recomandăm o primă recapitulare pe {primary_weakness} pentru a calibra profilul complet."
    )
    actions = [
        {"text": f"Recapitulează {primary_weakness.lower()} la prima ședință individuală", "done": False},
        {"text": "Colectează 2-3 rezultate suplimentare (teme, teste) pentru a rafina profilul", "done": False},
        {"text": "Regenerează profilul AI după prima săptămână de rezultate", "done": False},
    ]
    return why, actions



# ---------------------------------------------------------
# Screen B — Student page: 4 modes (Profiling, Exercise
# Generator, History & Progress, Test & Assignment Review)
# ---------------------------------------------------------

def _render_student_page(db, class_id, sid, active_tab="profil", worksheet=None,
                         difficulty=None, source_mode="mode1", test_insight=None):
    teacher_id = session["user_id"]

    classes = _teacher_classes(db, teacher_id)
    cls = next((c for c in classes if c.id == class_id), None)
    if not cls:
        return None

    student = _student_in_class(db, sid, class_id)
    if not student:
        return None

    metrics = db.get(Metric, sid)
    profile = db.get(Profile, sid)
    insight = db.get(AiInsight, sid)
    actions = json.loads(insight.recommended_actions_json) if insight and insight.recommended_actions_json else []

    chat_rows = db.scalars(
        select(ChatMessage).where(ChatMessage.student_id == sid).order_by(ChatMessage.id.asc())
    ).all()
    if not chat_rows:
        opener = (
            f"Bună! Sunt asistentul tău AI pentru {student.name}. "
            "Poți să mă întrebi lucruri precum „dă-mi un exercițiu de încălzire de 5 minute” "
            "sau „cum abordez ședința de recuperare de mâine”."
        )
        db.add(ChatMessage(student_id=sid, role="assistant", content=opener))
        db.commit()
        chat_rows = db.scalars(
            select(ChatMessage).where(ChatMessage.student_id == sid).order_by(ChatMessage.id.asc())
        ).all()

    chat_messages = [
        {"id": m.id, "role": m.role, "ts": m.ts, "content": markdown.markdown(m.content)}
        for m in chat_rows
    ]

    groups = db.execute(
        select(Group.id, Group.name)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.student_id == sid)
    ).mappings().all()

    test_records = db.scalars(
        select(TestRecord).where(TestRecord.student_id == sid).order_by(TestRecord.created_at.desc())
    ).all()

    history_summary = {
        "test_count": len(test_records),
        "chat_count": len([m for m in chat_messages if m["role"] == "teacher"]),
        "actions_done": len([a for a in actions if a.get("done")]),
        "actions_total": len(actions),
    }

    # Teacher's saved styles — same source Mode 2's menu.html card uses —
    # needed so the Mode 2 field block under the exercise generator select
    # offers the same style options.
    styles = db.scalars(
        select(Style).where(Style.user_id == teacher_id).order_by(Style.id.desc())
    ).all()

    return render_template(
        "clasa/elev_profil.html",
        classes=classes,
        selected_class=cls,
        student=student,
        metrics=metrics,
        profile=profile,
        insight=insight,
        actions=actions,
        chat_messages=chat_messages,
        current_groups=groups,
        active_tab=active_tab,
        worksheet=worksheet,
        difficulty=difficulty,
        source_mode=source_mode,
        source_mode_labels=SOURCE_MODE_LABELS,
        test_records=test_records,
        history_summary=history_summary,
        test_insight=test_insight,
        class_nav_base="/elevi",
        styles=styles,
    )


def student_page(db, apology, class_id, sid):
    active_tab = request.args.get("tab", "profil")
    page = _render_student_page(db, class_id, sid, active_tab=active_tab)
    if page is None:
        return apology("Elev sau clasă inexistentă", 404)
    return page


def _owned_student(db, sid):
    """A student is reachable only through a class the logged-in teacher owns."""
    return db.scalars(
        select(Student)
        .join(Class, Class.id == Student.class_id)
        .where(Student.id == sid, Class.teacher_id == session["user_id"])
    ).first()


def regenerate_profile(db, sid):
    # TODO: replace with real AI call — analyze metrics/history to produce
    # a fresh profile + insight instead of lightly rephrasing the existing one.
    student = _owned_student(db, sid)
    profile = db.get(Profile, sid) if student else None

    if student and profile:
        why = (
            f"Analiză reactualizată pentru {student.name}: progresul rămâne corelat cu "
            f"{profile.weaknesses}. Stil de învățare recomandat: {profile.learning_style}. "
            f"Durată de concentrare: {profile.attention_span or 'De evaluat'}."
        )
        actions = [
            {"text": f"Continuă exercițiile țintite pe {(profile.weaknesses or '').split(',')[0].strip().lower()}", "done": False},
            {"text": "Reevaluează nivelul de risc după următorul test", "done": False},
        ]
        insight = db.get(AiInsight, sid)
        if insight is None:
            insight = AiInsight(student_id=sid)
            db.add(insight)
        insight.why_struggling = why
        insight.recommended_actions_json = json.dumps(actions, ensure_ascii=False)
        db.commit()

    return redirect(request.referrer or "/elevi")


def toggle_action(db, apology, sid, idx):
    if not _owned_student(db, sid):
        return apology("Elev inexistent", 404)

    insight = db.get(AiInsight, sid)
    if not insight:
        return apology("Elev inexistent", 404)

    actions = json.loads(insight.recommended_actions_json) if insight.recommended_actions_json else []
    if 0 <= idx < len(actions):
        actions[idx]["done"] = not actions[idx]["done"]
        insight.recommended_actions_json = json.dumps(actions, ensure_ascii=False)
        db.commit()

    return redirect(request.referrer or "/elevi")


def chat_message(db, apology, sid):
    student = _owned_student(db, sid)
    if not student:
        return apology("Elev inexistent", 404)

    message = request.form.get("message", "").strip()
    if message:
        db.add(ChatMessage(student_id=sid, role="teacher", content=message))

        # Reuses the same generic math-teacher-assistant engine as Mode 1
        # (secondary.ai.assistant) — real model, mock fallback if no API key.
        profile = db.get(Profile, sid)
        context = (
            f"Ești un asistent AI care ajută un profesor cu elevul {student.name}. "
            f"Puncte forte: {profile.strengths if profile else '—'}. "
            f"Puncte slabe: {profile.weaknesses if profile else '—'}. "
            f"Stil de învățare: {profile.learning_style if profile else '—'}.\n"
            f"Întrebarea profesorului: {message}"
        )
        reply = ai.assistant(context)

        db.add(ChatMessage(student_id=sid, role="assistant", content=reply))
        db.commit()

    return redirect(request.referrer or "/elevi")


# ---------------------------------------------------------
# Mode 2 of 4 — Exercise generator (reuses secondary.ai.assistant,
# the same engine the 5 existing modes use). The style select now
# covers all 5 modes.
# ---------------------------------------------------------

DIFFICULTY_PROMPTS = {
    "usor": "exerciții mai ușoare, cu pași ghidați, pentru a reconstrui încrederea",
    "mediu": "exerciții de dificultate medie, potrivite nivelului clasei",
    "recapitulare": "un set de recapitulare mixtă, care combină mai multe subiecte conexe",
    "consolidare": "exerciții de consolidare finală, de nivel BAC, pentru verificarea stăpânirii complete",
}

SOURCE_MODE_PROMPTS = {
    "mode1": "Formulează exercițiile ca într-o conversație liberă cu un asistent AI de matematică, cu explicații scurte pentru context.",
    "mode2": "Formulează fiecare exercițiu ca un enunț în limbaj natural pe care elevul trebuie să îl traducă în limbaj matematic (expresii/ecuații), în stilul modului „Text → Matematică”.",
    "mode3": "Formulează exercițiile ca variante regenerate după un model de test existent, păstrând structura originală, în stilul modului „Creează după Model”.",
    "mode4": "Formulează exercițiile ca și cum ar fi transcrise dintr-o fișă scrisă de mână, în stilul modului „Transcriere Test Scris de Mână”.",
    "mode5": "Formulează exercițiile în stilul unei variante de BAC oficiale, cu subpuncte a), b), c) și barem implicit, în stilul modului „Generator BAC”.",
}
SOURCE_MODE_LABELS = {
    "mode1": "Asistent AI (Mod 1)",
    "mode2": "Text → Matematică (Mod 2)",
    "mode3": "Creează după Model (Mod 3)",
    "mode4": "Transcriere Scris de Mână (Mod 4)",
    "mode5": "Generator BAC (Mod 5)",
}


def exercises_redirect(db, apology, sid):
    student = _owned_student(db, sid)
    if not student:
        return apology("Elev inexistent", 404)
    return redirect(f"/elevi/{student.class_id}/{sid}?tab=exercitii")


def _mode_specific_prompt_fragment(db, teacher_id, source_mode):
    """Reads the same fields the selected mode's own menu.html card collects
    (submitted alongside the exercise-generator form) and turns them into a
    prompt fragment, so picking e.g. Mode 5 in the style selector also lets
    the teacher fill in that mode's "Lecții principale" / "Lecții de omis"."""
    if source_mode == "mode2":
        style_id = request.form.get("m2_style", "").strip()
        school_class = request.form.get("m2_school_class", "").strip()
        bac = request.form.get("m2_bac", "").strip()
        style_name = "Stil implicit"
        if style_id.isdigit():
            style_row = db.scalars(
                select(Style).where(Style.id == int(style_id), Style.user_id == teacher_id)
            ).first()
            if style_row:
                style_name = style_row.style_name
        parts = [f"Stil de generare: {style_name}."]
        if school_class:
            parts.append(f"Clasa: a {school_class}-a.")
        if bac:
            parts.append(f"Versiune BAC: {bac}.")
        return " ".join(parts)

    if source_mode == "mode3":
        prompt_text = request.form.get("m3_prompt", "").strip()
        differences = request.form.get("m3_differences", "").strip()
        filename = _save_upload(request.files.get("m3_file"))
        parts = []
        if filename:
            parts.append(f"Model încărcat: {filename}.")
        if prompt_text:
            parts.append(f"Instrucțiuni: {prompt_text}.")
        if differences:
            parts.append(f"Diferențe față de model: {differences}.")
        return " ".join(parts)

    if source_mode == "mode4":
        prompt_text = request.form.get("m4_prompt", "").strip()
        differences = request.form.get("m4_differences", "").strip()
        filename = _save_upload(request.files.get("m4_file"))
        parts = []
        if filename:
            parts.append(f"Fișă scrisă de mână încărcată: {filename}.")
        if prompt_text:
            parts.append(f"Instrucțiuni generare: {prompt_text}.")
        if differences:
            parts.append(f"Diferențe față de original: {differences}.")
        return " ".join(parts)

    if source_mode == "mode5":
        lessons = request.form.get("m5_lessons", "").strip()
        avoid = request.form.get("m5_avoid", "").strip()
        parts = []
        if lessons:
            parts.append(f"Lecții principale de acoperit: {lessons}.")
        if avoid:
            parts.append(f"Lecții de omis: {avoid}.")
        return " ".join(parts)

    return ""


def generate_exercises(db, apology, sid):
    student = _owned_student(db, sid)
    if not student:
        return apology("Elev inexistent", 404)

    profile = db.get(Profile, sid)
    difficulty = request.form.get("difficulty", "mediu")
    difficulty_desc = DIFFICULTY_PROMPTS.get(difficulty, DIFFICULTY_PROMPTS["mediu"])
    source_mode = request.form.get("source_mode", "mode1")
    source_mode_desc = SOURCE_MODE_PROMPTS.get(source_mode, SOURCE_MODE_PROMPTS["mode1"])
    weaknesses = profile.weaknesses if profile else "algebră generală"
    mode_fields_desc = _mode_specific_prompt_fragment(db, session["user_id"], source_mode)

    prompt = (
        "Genereaza un set de 5 exerciții de matematică, numerotate, cu enunț clar, "
        f"axate pe următoarele puncte slabe ale elevului: {weaknesses}. "
        f"Nivel de dificultate: {difficulty_desc}. "
        f"Stil de formulare: {source_mode_desc} "
        + (f"{mode_fields_desc} " if mode_fields_desc else "")
        + "Nu include rezolvările, doar enunțurile, pregătite pentru tipărire ca fișă de lucru."
    )

    # Reuses the exact same generation engine as Mode 1 (secondary.ai.assistant) —
    # TODO: replace with real AI call once a dedicated worksheet model is wired in.
    worksheet = markdown.markdown(ai.assistant(prompt))

    page = _render_student_page(
        db, student.class_id, sid,
        active_tab="exercitii", worksheet=worksheet, difficulty=difficulty, source_mode=source_mode,
    )
    if page is None:
        return apology("Elev sau clasă inexistentă", 404)
    return page


# ---------------------------------------------------------
# Mode 4 of 4 — Test & Assignment Review: upload the given
# test + the student's handwritten solution, get AI insights.
# Shared by the recurring "Recenzie" tab (this function) and by
# the one-time Add Student flow (_mock_test_insight, above).
# ---------------------------------------------------------

def submit_test_review(db, apology, sid):
    student = _owned_student(db, sid)
    if not student:
        return apology("Elev inexistent", 404)

    grade = request.form.get("grade", "").strip() or None
    lessons = request.form.get("lessons", "").strip() or None
    test_filename = _save_upload(request.files.get("test_file"))
    solution_filename = _save_upload(request.files.get("solution_file"))

    insights = _mock_test_insight(student.name, lessons, test_filename, solution_filename)

    db.add(TestRecord(
        student_id=sid, grade=_to_grade(grade), lessons=lessons,
        test_filename=test_filename, solution_filename=solution_filename,
        ai_insights=insights,
    ))
    db.commit()

    page = _render_student_page(
        db, student.class_id, sid, active_tab="recenzie", test_insight=insights,
    )
    if page is None:
        return apology("Elev sau clasă inexistentă", 404)
    return page


# ---------------------------------------------------------
# Screen C — Smart Groups board
# ---------------------------------------------------------

def groups_page(db, apology, class_id):
    teacher_id = session["user_id"]
    classes = _teacher_classes(db, teacher_id)
    selected_class = next((c for c in classes if c.id == class_id), None)
    if not selected_class:
        return apology("Clasă inexistentă", 404)

    groups = db.scalars(
        select(Group).where(Group.class_id == class_id).order_by(Group.id.asc())
    ).all()

    dirty = False
    for g in groups:
        if not g.description:
            g.description = _generate_group_description(g.weakness_tag)
            dirty = True
    if dirty:
        db.commit()

    board = []
    for g in groups:
        members = db.execute(
            select(Student.id, Student.name, Metric.risk_level)
            .join(GroupMember, GroupMember.student_id == Student.id)
            .outerjoin(Metric, Metric.student_id == Student.id)
            .where(GroupMember.group_id == g.id)
        ).mappings().all()
        board.append({"group": g, "members": members})

    unassigned = db.execute(
        select(Student.id, Student.name, Metric.risk_level)
        .outerjoin(Metric, Metric.student_id == Student.id)
        .where(
            Student.class_id == class_id,
            Student.id.not_in(select(GroupMember.student_id)),
        )
    ).mappings().all()

    return render_template(
        "clasa/grupe.html",
        classes=classes,
        selected_class=selected_class,
        board=board,
        unassigned=unassigned,
        class_nav_base="/elevi",
        class_nav_suffix="/grupe",
    )


def auto_group(db, apology, class_id):
    # TODO: replace with real AI call — currently re-clusters students using
    # the same fractions/functions/advanced keyword heuristic used at seed time.
    if not _owned_class(db, session["user_id"], class_id):
        return apology("Clasă inexistentă", 404)

    students = db.execute(
        select(Student.id, Profile.weaknesses, Metric.risk_level)
        .outerjoin(Profile, Profile.student_id == Student.id)
        .outerjoin(Metric, Metric.student_id == Student.id)
        .where(Student.class_id == class_id)
    ).mappings().all()

    groups = db.scalars(
        select(Group).where(Group.class_id == class_id).order_by(Group.id.asc())
    ).all()
    group_by_tag = {g.weakness_tag: g.id for g in groups}
    if not group_by_tag:
        return redirect(f"/elevi/{class_id}/grupe")

    db.execute(
        delete(GroupMember).where(
            GroupMember.group_id.in_(select(Group.id).where(Group.class_id == class_id))
        )
    )

    seen = set()
    for s in students:
        weaknesses = (s["weaknesses"] or "").lower()
        if "fracți" in weaknesses:
            key = "fractii"
        elif "func" in weaknesses:
            key = "functii"
        elif s["risk_level"] == "Scăzut":
            key = "avansat"
        else:
            key = "functii"

        target = group_by_tag.get(key) or next(iter(group_by_tag.values()))
        if (target, s["id"]) in seen:
            continue
        seen.add((target, s["id"]))
        db.add(GroupMember(group_id=target, student_id=s["id"]))

    db.commit()
    return redirect(f"/elevi/{class_id}/grupe")


def move_group_member(db, apology, class_id):
    student_id = request.form.get("student_id", type=int)
    group_id = request.form.get("group_id", type=int)

    if not student_id or not group_id:
        return apology("Date lipsă", 400)

    if not _owned_class(db, session["user_id"], class_id):
        return apology("Clasă inexistentă", 404)

    db.execute(delete(GroupMember).where(GroupMember.student_id == student_id))
    db.add(GroupMember(group_id=group_id, student_id=student_id))
    db.commit()

    return jsonify({"ok": True})


# ---------------------------------------------------------
# Group detail — suggested actions for the whole group +
# a group-scoped exercise generator (same reuse of ai.assistant
# as the per-student one, just fed the group's shared weakness).
# ---------------------------------------------------------

def group_detail(db, apology, class_id, gid, worksheet=None, difficulty=None, source_mode="mode1"):
    teacher_id = session["user_id"]
    classes = _teacher_classes(db, teacher_id)
    selected_class = next((c for c in classes if c.id == class_id), None)
    if not selected_class:
        return apology("Clasă inexistentă", 404)

    group = db.scalars(
        select(Group).where(Group.id == gid, Group.class_id == class_id)
    ).first()
    if not group:
        return apology("Grupă inexistentă", 404)

    members = db.execute(
        select(Student.id, Student.name, Metric.risk_level, Profile.weaknesses)
        .join(GroupMember, GroupMember.student_id == Student.id)
        .outerjoin(Metric, Metric.student_id == Student.id)
        .outerjoin(Profile, Profile.student_id == Student.id)
        .where(GroupMember.group_id == gid)
    ).mappings().all()

    suggested_actions = json.loads(group.suggested_actions_json) if group.suggested_actions_json else []
    if not suggested_actions:
        suggested_actions = _default_group_actions(group.name)
        group.suggested_actions_json = json.dumps(suggested_actions, ensure_ascii=False)
        db.commit()

    return render_template(
        "clasa/grupa_detaliu.html",
        classes=classes,
        selected_class=selected_class,
        group=group,
        members=members,
        suggested_actions=suggested_actions,
        worksheet=worksheet,
        difficulty=difficulty,
        source_mode=source_mode,
        source_mode_labels=SOURCE_MODE_LABELS,
        class_nav_base="/elevi",
        class_nav_suffix="/grupe",
    )


def _default_group_actions(group_name):
    # TODO: replace with real AI call — currently a templated placeholder,
    # same boundary as the per-student recommended actions.
    return [
        {"text": f"Planifică o sesiune de 15 minute dedicată punctului comun al {group_name.lower()}", "done": False},
        {"text": "Folosește un exercițiu comun de încălzire pentru tot grupul înainte de tema individuală", "done": False},
        {"text": "Reevaluează componența grupei după următorul test", "done": False},
    ]


def _owned_group(db, gid):
    return db.scalars(
        select(Group)
        .join(Class, Class.id == Group.class_id)
        .where(Group.id == gid, Class.teacher_id == session["user_id"])
    ).first()


def regenerate_group_actions(db, apology, gid):
    group = _owned_group(db, gid)
    if not group:
        return apology("Grupă inexistentă", 404)

    # TODO: replace with real AI call — see _default_group_actions.
    actions = _default_group_actions(group.name)
    group.suggested_actions_json = json.dumps(actions, ensure_ascii=False)
    db.commit()

    return redirect(request.referrer or "/elevi")


def toggle_group_action(db, apology, gid, idx):
    group = _owned_group(db, gid)
    if not group:
        return apology("Grupă inexistentă", 404)

    actions = json.loads(group.suggested_actions_json) if group.suggested_actions_json else []
    if 0 <= idx < len(actions):
        actions[idx]["done"] = not actions[idx]["done"]
        group.suggested_actions_json = json.dumps(actions, ensure_ascii=False)
        db.commit()

    return redirect(request.referrer or "/elevi")


def generate_group_exercises(db, apology, class_id, gid):
    group = db.scalars(
        select(Group).where(Group.id == gid, Group.class_id == class_id)
    ).first()
    if not group or not _owned_class(db, session["user_id"], class_id):
        return apology("Grupă inexistentă", 404)

    members = db.scalars(
        select(Student.name)
        .join(GroupMember, GroupMember.student_id == Student.id)
        .where(GroupMember.group_id == gid)
    ).all()
    member_names = ", ".join(members) or "elevii grupei"

    difficulty = request.form.get("difficulty", "mediu")
    difficulty_desc = DIFFICULTY_PROMPTS.get(difficulty, DIFFICULTY_PROMPTS["mediu"])
    source_mode = request.form.get("source_mode", "mode1")
    source_mode_desc = SOURCE_MODE_PROMPTS.get(source_mode, SOURCE_MODE_PROMPTS["mode1"])

    prompt = (
        f"Genereaza un set de 5 exerciții de matematică, numerotate, cu enunț clar, potrivite pentru "
        f"un grup de elevi ({member_names}) care au în comun dificultăți la: {group.weakness_tag}. "
        f"Nivel de dificultate: {difficulty_desc}. "
        f"Stil de formulare: {source_mode_desc} "
        "Nu include rezolvările, doar enunțurile, pregătite pentru tipărire ca fișă de lucru comună grupei."
    )

    # Same generation engine reused again — secondary.ai.assistant —
    # TODO: replace with real AI call once a dedicated worksheet model is wired in.
    worksheet = markdown.markdown(ai.assistant(prompt))

    return group_detail(db, apology, class_id, gid,
                        worksheet=worksheet, difficulty=difficulty, source_mode=source_mode)
