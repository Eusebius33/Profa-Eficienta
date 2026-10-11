import json
import os
import markdown
from collections import Counter
from datetime import datetime

from docx import Document
from PyPDF2 import PdfReader
from flask import render_template, request, send_file, session, redirect, jsonify
from sqlalchemy import delete, or_, select
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


# ---------------------------------------------------------
# Reading what the teacher uploaded
#
# A test/solution is only useful once its contents are text:
# PDFs and .docx carry their own, photos and scanned PDFs go
# through Gemini vision (the same transcriber Mode 4 uses).
# ---------------------------------------------------------

UPLOAD_FOLDER = "uploads"
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def upload_path(filename):
    return os.path.join(UPLOAD_FOLDER, filename)


def _pdf_text(path):
    try:
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as error:
        print(f"[classroom] could not read PDF {path}: {error}", flush=True)
        return ""


def read_uploaded_document(filename):
    """Text of an uploaded page, or "" when it cannot be read.

    A PDF that yields no extractable text is a scan, so it falls through to the
    vision transcriber rather than being reported as an empty paper.
    """
    if not filename:
        return ""

    path = upload_path(filename)
    if not os.path.exists(path):
        return ""

    extension = os.path.splitext(path)[1].lower()

    if extension == ".pdf":
        native = _pdf_text(path)
        if len(native) >= 40:
            return native

    if extension == ".pdf" or extension in _IMAGE_EXTENSIONS:
        transcript = ai.transcribe_handwriting(path)
        return "" if ai.is_error(transcript) else (transcript or "").strip()

    if extension == ".docx":
        try:
            return "\n".join(p.text for p in Document(path).paragraphs).strip()
        except Exception as error:
            print(f"[classroom] could not read docx {path}: {error}", flush=True)
            return ""

    if extension == ".txt":
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read().strip()
        except OSError:
            return ""

    return ""


# ---------------------------------------------------------
# Risk metrics, computed from the student's actual results.
#
# Every column on the risk overview is derived here, from the
# test records the teacher entered plus the attendance they
# set. Nothing on that table is a stored constant any more,
# so adding a result moves the numbers.
# ---------------------------------------------------------

MAX_GRADE = 10.0
_FAILING_GRADE = 5.0


def _recency_weighted_mean(values):
    """Mean that leans on recent results, so improvement shows up quickly.

    `values` is oldest-first; weights ramp 1, 2, 3... which gives the newest
    paper the most pull without letting it erase the history.
    """
    if not values:
        return None
    weights = range(1, len(values) + 1)
    total = sum(v * w for v, w in zip(values, weights))
    return total / sum(weights)


def _trend_from(grades):
    """'up' / 'down' / 'stable' by comparing the newer half against the older."""
    if len(grades) < 2:
        return "stable"
    midpoint = len(grades) // 2
    older, newer = grades[:midpoint], grades[midpoint:]
    if not older or not newer:
        return "stable"
    delta = (sum(newer) / len(newer)) - (sum(older) / len(older))
    if delta > 0.3:
        return "up"
    if delta < -0.3:
        return "down"
    return "stable"


def _risk_from(avg_grade, attendance, trend, completion_pct):
    """The three risk bands, in the order a teacher would triage them."""
    attendance = attendance if attendance is not None else 100

    if avg_grade is None:
        # No graded work yet - attendance is the only signal there is.
        if attendance < 75:
            return "Ridicat"
        return "Mediu"

    if avg_grade < 5.5 or attendance < 75 or completion_pct < 40:
        return "Ridicat"
    if trend == "down" and avg_grade < 6.5:
        return "Ridicat"
    if avg_grade >= 7.5 and attendance >= 88 and trend != "down":
        return "Scăzut"
    return "Mediu"


def _repeated_mistake_count(records):
    """How many distinct error tags show up on more than one paper.

    Prefers the tags the AI review extracted; falls back to the lesson label of
    failed papers when a record was entered without an uploaded solution.
    """
    occurrences = Counter()
    for record in records:
        tags = set()
        if record.mistake_tags_json:
            try:
                parsed = json.loads(record.mistake_tags_json)
                tags = {str(t).strip().lower() for t in parsed if str(t).strip()}
            except (ValueError, TypeError):
                tags = set()
        if not tags and record.grade is not None and record.grade < _FAILING_GRADE:
            tags = {(record.lessons or "").strip().lower()} - {""}
        occurrences.update(tags)

    return sum(1 for _, count in occurrences.items() if count >= 2)


def recompute_metrics(db, sid, attendance=None):
    """Rebuild a student's metrics row from their results. Returns the row.

    Called after anything that changes the evidence - a new result, an edited
    attendance figure, a regenerated profile - so the risk overview is always a
    view of the data rather than a snapshot taken when the student was added.
    """
    metrics = db.get(Metric, sid)
    if metrics is None:
        metrics = Metric(student_id=sid)
        db.add(metrics)

    if attendance is not None:
        metrics.attendance = max(0, min(100, attendance))

    records = db.scalars(
        select(TestRecord)
        .where(TestRecord.student_id == sid)
        .order_by(TestRecord.created_at.asc(), TestRecord.id.asc())
    ).all()

    grades = [r.grade for r in records if r.grade is not None]

    if grades:
        metrics.avg_grade = round(sum(grades) / len(grades), 2)
        weighted = _recency_weighted_mean(grades)
        metrics.mastery_pct = int(round(weighted / MAX_GRADE * 100))
    else:
        metrics.avg_grade = None
        metrics.mastery_pct = None

    # Completion = the share of recorded work that actually came back graded,
    # blended with how many of the recommended actions have been ticked off.
    if records:
        graded_share = len(grades) / len(records)
    else:
        graded_share = None

    insight = db.get(AiInsight, sid)
    actions = []
    if insight and insight.recommended_actions_json:
        try:
            actions = json.loads(insight.recommended_actions_json)
        except (ValueError, TypeError):
            actions = []
    action_share = (
        len([a for a in actions if a.get("done")]) / len(actions) if actions else None
    )

    parts = [p for p in (graded_share, action_share) if p is not None]
    metrics.completion_pct = int(round(sum(parts) / len(parts) * 100)) if parts else None

    times = [r.minutes_per_exercise for r in records if r.minutes_per_exercise]
    if times:
        average = sum(times) / len(times)
        metrics.avg_time_per_ex = f"{average:.0f} min/ex" if average >= 1 else f"{average:.1f} min/ex"
    else:
        metrics.avg_time_per_ex = None

    metrics.repeated_mistakes = _repeated_mistake_count(records)
    metrics.risk_trend = _trend_from(grades)
    metrics.risk_level = _risk_from(
        metrics.avg_grade,
        metrics.attendance,
        metrics.risk_trend,
        metrics.completion_pct if metrics.completion_pct is not None else 100,
    )
    metrics.updated_at = datetime.utcnow()

    # profiles.risk_level is the copy the profile card reads; keep the two from
    # drifting apart now that the metric one actually moves.
    profile = db.get(Profile, sid)
    if profile is not None:
        profile.risk_level = metrics.risk_level

    return metrics


def _evidence_summary(db, sid, student_name):
    """The block of real data every classroom AI prompt is grounded in."""
    metrics = db.get(Metric, sid)
    profile = db.get(Profile, sid)
    records = db.scalars(
        select(TestRecord)
        .where(TestRecord.student_id == sid)
        .order_by(TestRecord.created_at.asc(), TestRecord.id.asc())
    ).all()

    lines = [f"Elev: {student_name}"]
    if metrics:
        lines.append(
            f"Prezență: {metrics.attendance if metrics.attendance is not None else '—'}%. "
            f"Media notelor: {metrics.avg_grade if metrics.avg_grade is not None else 'fără note'}. "
            f"Stăpânire: {metrics.mastery_pct if metrics.mastery_pct is not None else '—'}%. "
            f"Tendință: {metrics.risk_trend}. Greșeli repetate: {metrics.repeated_mistakes}."
        )
    if profile:
        lines.append(
            f"Observațiile profesorului — personalitate: {profile.personality_traits or '—'}; "
            f"concentrare: {profile.attention_span or '—'}; "
            f"absențe: {profile.absent_lessons or '—'}."
        )
        if profile.weaknesses:
            lines.append(f"Puncte slabe notate până acum: {profile.weaknesses}.")

    if records:
        lines.append("Rezultate înregistrate (de la cel mai vechi la cel mai nou):")
        for record in records:
            grade = record.grade if record.grade is not None else "fără notă"
            lines.append(f"  - {record.lessons or 'lecție nespecificată'}: {grade}")
            if record.transcript:
                lines.append(f"    transcriere lucrare: {record.transcript[:1200]}")
    else:
        lines.append("Nu există încă nicio lucrare înregistrată.")

    return "\n".join(lines)


# ---------------------------------------------------------
# AI analysis, each with a deterministic fallback.
#
# When the model is unavailable classroom_json() returns
# None and these fall back to a summary computed from the
# same numbers - the teacher still gets something true,
# just shorter, and `ai_generated` says which one it was.
# ---------------------------------------------------------

_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "strengths": {"type": "string"},
        "weaknesses": {"type": "string"},
        "learning_style": {"type": "string"},
        "confidence": {"type": "string", "enum": ["Scăzută", "Medie", "Ridicată"]},
        "why_struggling": {"type": "string"},
        "recommended_actions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 5,
        },
    },
    "required": [
        "strengths", "weaknesses", "learning_style", "confidence",
        "why_struggling", "recommended_actions",
    ],
}

_CONFIDENCE_VALUES = {"Scăzută", "Medie", "Ridicată"}


def _fallback_profile(student_name, metrics, profile):
    """Deterministic profile summary, stated as the computed facts it is."""
    avg = metrics.avg_grade if metrics else None
    attendance = metrics.attendance if metrics else None
    trend = metrics.risk_trend if metrics else "stable"
    trend_words = {"up": "în creștere", "down": "în scădere", "stable": "constantă"}
    weaknesses = (profile.weaknesses if profile else None) or "De evaluat"
    primary = weaknesses.split(",")[0].strip()

    if avg is None:
        why = (
            f"Încă nu există note înregistrate pentru {student_name}, deci profilul nu poate fi "
            f"calculat. Prezența notată este {attendance if attendance is not None else '—'}%. "
            "Adaugă 2-3 rezultate din tabul „Recenzie” pentru a obține o analiză reală."
        )
    else:
        why = (
            f"Media calculată pentru {student_name} este {avg} din {int(MAX_GRADE)}, pe baza "
            f"rezultatelor înregistrate, cu o evoluție {trend_words.get(trend, 'constantă')} și o "
            f"prezență de {attendance if attendance is not None else '—'}%. "
            f"Zona cu cele mai multe dificultăți notate rămâne {primary.lower()}. "
            "(Analiza AI detaliată nu a fost disponibilă — acesta este rezumatul calculat din date.)"
        )

    actions = [
        f"Recapitulează {primary.lower()} la următoarea ședință",
        "Adaugă rezultatul următoarei lucrări pentru a reactualiza profilul",
    ]
    if attendance is not None and attendance < 80:
        actions.append(f"Discută absențele — prezența este {attendance}%")
    if trend == "down":
        actions.append("Evoluția este în scădere: verifică ce s-a schimbat în ultimele lecții")

    return {
        "strengths": (profile.strengths if profile else None) or "De evaluat",
        "weaknesses": weaknesses,
        "learning_style": (profile.learning_style if profile else None) or "De evaluat",
        "confidence": (profile.confidence if profile else None) or "Medie",
        "why_struggling": why,
        "recommended_actions": actions,
        "ai_generated": False,
    }


def analyze_student(db, sid, student_name):
    """Real AI profile + insight for a student, grounded in their results."""
    metrics = db.get(Metric, sid)
    profile = db.get(Profile, sid)

    prompt = (
        "Analizează elevul pe baza datelor de mai jos și întoarce profilul lui.\n\n"
        f"{_evidence_summary(db, sid, student_name)}\n\n"
        "Cerințe:\n"
        "- `strengths` și `weaknesses`: liste scurte separate prin virgulă, cu capitole de "
        "matematică deduse DOAR din rezultatele și observațiile de mai sus.\n"
        "- `learning_style`: cum ar trebui predat concret acestui elev.\n"
        "- `confidence`: exact una din valorile Scăzută / Medie / Ridicată.\n"
        "- `why_struggling`: 2-4 propoziții care explică situația, citând notele reale.\n"
        "- `recommended_actions`: 3-4 acțiuni concrete pentru profesor."
    )

    result = ai.classroom_json(prompt, schema=_PROFILE_SCHEMA, temperature=0.4)
    if not result:
        return _fallback_profile(student_name, metrics, profile)

    actions = result.get("recommended_actions") or []
    if not isinstance(actions, list) or not actions:
        return _fallback_profile(student_name, metrics, profile)

    confidence = str(result.get("confidence", "")).strip()
    fallback = _fallback_profile(student_name, metrics, profile)

    return {
        "strengths": str(result.get("strengths") or fallback["strengths"]).strip(),
        "weaknesses": str(result.get("weaknesses") or fallback["weaknesses"]).strip(),
        "learning_style": str(result.get("learning_style") or fallback["learning_style"]).strip(),
        "confidence": confidence if confidence in _CONFIDENCE_VALUES else fallback["confidence"],
        "why_struggling": str(result.get("why_struggling") or fallback["why_struggling"]).strip(),
        "recommended_actions": [str(a).strip() for a in actions if str(a).strip()][:5],
        "ai_generated": True,
    }


def _apply_analysis(db, sid, analysis):
    """Write an analyze_student() result onto the profile + insight rows."""
    profile = db.get(Profile, sid)
    if profile is None:
        profile = Profile(student_id=sid)
        db.add(profile)
    profile.strengths = analysis["strengths"]
    profile.weaknesses = analysis["weaknesses"]
    profile.learning_style = analysis["learning_style"]
    profile.confidence = analysis["confidence"]

    insight = db.get(AiInsight, sid)
    if insight is None:
        insight = AiInsight(student_id=sid)
        db.add(insight)
    insight.why_struggling = analysis["why_struggling"]

    # Preserve ticks on actions whose wording survived the regeneration.
    previously_done = set()
    if insight.recommended_actions_json:
        try:
            for action in json.loads(insight.recommended_actions_json):
                if action.get("done"):
                    previously_done.add(action.get("text"))
        except (ValueError, TypeError):
            pass

    insight.recommended_actions_json = json.dumps(
        [{"text": text, "done": text in previously_done} for text in analysis["recommended_actions"]],
        ensure_ascii=False,
    )
    return profile, insight


_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "insight": {"type": "string"},
        "mistake_tags": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "suggested_grade": {"type": "number"},
    },
    "required": ["insight", "mistake_tags"],
}


def review_test(student_name, lessons, grade, test_text, solution_text):
    """Grade a handwritten paper against the test it answers.

    Returns (insight, mistake_tags, transcript, ai_generated). With no readable
    upload it still returns a truthful note instead of inventing an analysis.
    """
    transcript_parts = []
    if test_text:
        transcript_parts.append(f"=== SUBIECT ===\n{test_text}")
    if solution_text:
        transcript_parts.append(f"=== REZOLVAREA ELEVULUI ===\n{solution_text}")
    transcript = "\n\n".join(transcript_parts)

    if not transcript:
        note = f"Rezultat înregistrat pentru {student_name}"
        if lessons:
            note += f" la {lessons}"
        if grade is not None:
            note += f", nota {grade}"
        note += (
            ". Nu a fost încărcată nicio lucrare lizibilă, deci nu există analiză pe greșeli — "
            "încarcă poza subiectului și a rezolvării pentru o recenzie detaliată."
        )
        return note, [], "", False

    prompt = (
        f"Analizează lucrarea elevului {student_name}"
        + (f" la capitolul {lessons}" if lessons else "")
        + (f". Nota acordată de profesor: {grade}" if grade is not None else "")
        + ".\n\nMai jos este transcrierea paginilor încărcate.\n\n"
        + transcript[:12000]
        + "\n\nCerințe:\n"
        "- `insight`: 3-5 propoziții pentru profesor, care numesc greșelile CONCRETE găsite în "
        "rezolvare (pas greșit, regulă aplicată greșit) și ce de recapitulat. Dacă transcrierea "
        "este prea neclară pentru a identifica greșeli, spune exact asta.\n"
        "- `mistake_tags`: 1-5 etichete scurte (2-4 cuvinte) pentru tipul fiecărei greșeli, "
        "ex. „erori de semn”, „simplificare fracții”. Listă goală dacă lucrarea e corectă.\n"
        "- `suggested_grade`: nota pe care ai acorda-o tu, de la 1 la 10."
    )

    result = ai.classroom_json(prompt, schema=_REVIEW_SCHEMA, temperature=0.3)

    if not result or not str(result.get("insight") or "").strip():
        note = (
            f"Lucrarea pentru {student_name}"
            + (f" ({lessons})" if lessons else "")
            + " a fost încărcată și transcrisă, dar analiza AI nu a fost disponibilă. "
            "Transcrierea este salvată mai jos și poate fi reanalizată mai târziu."
        )
        return note, [], transcript, False

    tags = result.get("mistake_tags") or []
    tags = [str(t).strip() for t in tags if str(t).strip()][:6] if isinstance(tags, list) else []

    insight = str(result["insight"]).strip()
    suggested = result.get("suggested_grade")
    if isinstance(suggested, (int, float)) and 1 <= suggested <= 10:
        insight += f"\n\nNotă sugerată de AI: {round(float(suggested), 1)}."

    return insight, tags, transcript, True


_GROUP_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "actions": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5},
    },
    "required": ["name", "description", "actions"],
}


def analyze_group(topic, members):
    """Name, describe and plan a group from its real members.

    `members` is a list of {name, risk_level, weaknesses, avg_grade} dicts.
    """
    roster = "\n".join(
        f"  - {m['name']}: risc {m.get('risk_level') or '—'}, "
        f"media {m.get('avg_grade') if m.get('avg_grade') is not None else '—'}, "
        f"puncte slabe: {m.get('weaknesses') or '—'}"
        for m in members
    ) or "  (grupă fără elevi)"

    prompt = (
        f"O grupă de lucru a fost formată în jurul dificultății comune: „{topic}”.\n"
        f"Membrii grupei:\n{roster}\n\n"
        "Cerințe:\n"
        "- `name`: un nume scurt de grupă în română, care numește dificultatea comună "
        "(ex. „Grupa Fracții”, „Grupa Derivate — aprofundare”). Maxim 40 de caractere.\n"
        "- `description`: 2 propoziții despre ce au în comun ACEȘTI elevi și cum ar trebui "
        "abordată grupa.\n"
        "- `actions`: 3 acțiuni concrete pentru profesor cu această grupă."
    )

    result = ai.classroom_json(prompt, schema=_GROUP_SCHEMA, temperature=0.5)

    label = topic.strip().capitalize() if topic else "Diverse"
    fallback_name = f"Grupa {label}"[:60]
    fallback_description = (
        f"Grupă formată din {len(members)} elev(i) cu dificultăți la {label.lower()}: "
        + ", ".join(m["name"] for m in members[:6])
        + ("." if len(members) <= 6 else ", ...")
        + " (Descrierea AI nu a fost disponibilă.)"
    )
    fallback_actions = [
        f"Planifică o sesiune comună de {label.lower()}",
        "Dă un exercițiu comun de încălzire înainte de tema individuală",
        "Reevaluează componența grupei după următoarea lucrare",
    ]

    if not result:
        return fallback_name, fallback_description, fallback_actions, False

    actions = result.get("actions") or []
    actions = [str(a).strip() for a in actions if str(a).strip()] if isinstance(actions, list) else []

    return (
        (str(result.get("name") or fallback_name).strip() or fallback_name)[:60],
        str(result.get("description") or fallback_description).strip(),
        actions[:5] or fallback_actions,
        True,
    )


_GROUPS_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "actions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                },
                "required": ["topic", "name", "description", "actions"],
            },
        }
    },
    "required": ["groups"],
}


def analyze_groups(clusters):
    """Name, describe and plan every group of a class in ONE call.

    `clusters` is the [(topic, members)] list cluster_by_weakness() returns.
    Doing this per group cost one request each, which a 20-request-per-day
    Gemini free tier cannot carry for a class with six groups - so the whole
    board is described in a single request and matched back up by topic.

    Returns {topic: (name, description, actions)}, falling back per group.
    """
    fallbacks = {}
    for topic, members in clusters:
        label = (topic or "diverse").strip().capitalize()
        fallbacks[topic] = (
            f"Grupa {label}"[:60],
            f"Grupă formată din {len(members)} elev(i) cu dificultăți la {label.lower()}: "
            + ", ".join(m["name"] for m in members[:6])
            + ("." if len(members) <= 6 else ", ...")
            + " (Descrierea AI nu a fost disponibilă.)",
            [
                f"Planifică o sesiune comună de {label.lower()}",
                "Dă un exercițiu comun de încălzire înainte de tema individuală",
                "Reevaluează componența grupei după următoarea lucrare",
            ],
        )

    if not clusters:
        return fallbacks

    roster_blocks = []
    for topic, members in clusters:
        roster = "\n".join(
            f"    - {m['name']}: risc {m.get('risk_level') or '—'}, "
            f"media {m.get('avg_grade') if m.get('avg_grade') is not None else '—'}, "
            f"puncte slabe: {m.get('weaknesses') or '—'}"
            for m in members
        )
        roster_blocks.append(f'  topic „{topic}”:\n{roster}')

    prompt = (
        "O clasă a fost împărțită în grupe de lucru după dificultatea comună a elevilor.\n"
        "Grupele și membrii lor:\n\n" + "\n\n".join(roster_blocks) + "\n\n"
        "Pentru FIECARE grupă întoarce un obiect în lista `groups`, cu:\n"
        "- `topic`: exact string-ul topicului primit, ca să le pot potrivi.\n"
        "- `name`: nume scurt de grupă în română, maxim 40 de caractere.\n"
        "- `description`: 2 propoziții despre ce au în comun ACEȘTI elevi și cum se abordează.\n"
        "- `actions`: 3 acțiuni concrete pentru profesor cu grupa.\n"
        "Întoarce exact câte grupe ai primit, în aceeași ordine."
    )

    result = ai.classroom_json(prompt, schema=_GROUPS_BATCH_SCHEMA, temperature=0.5)
    if not result or not isinstance(result.get("groups"), list):
        return fallbacks

    by_topic = {}
    for entry in result["groups"]:
        if isinstance(entry, dict) and entry.get("topic") is not None:
            by_topic[str(entry["topic"]).strip()] = entry

    analyzed = {}
    for index, (topic, _members) in enumerate(clusters):
        entry = by_topic.get(str(topic).strip())
        if entry is None and index < len(result["groups"]):
            # The model dropped or renamed the topic key; fall back to order.
            candidate = result["groups"][index]
            entry = candidate if isinstance(candidate, dict) else None
        if entry is None:
            analyzed[topic] = fallbacks[topic]
            continue

        actions = entry.get("actions") or []
        actions = [str(a).strip() for a in actions if str(a).strip()] if isinstance(actions, list) else []
        analyzed[topic] = (
            (str(entry.get("name") or fallbacks[topic][0]).strip() or fallbacks[topic][0])[:60],
            str(entry.get("description") or fallbacks[topic][1]).strip(),
            actions[:5] or fallbacks[topic][2],
        )

    return analyzed


# ---------------------------------------------------------
# Clustering students into groups by what they actually
# struggle with, instead of three hardcoded keyword buckets.
# ---------------------------------------------------------

_STOPWORD_TAGS = {"", "de evaluat", "none", "-", "—"}
_MAX_GROUPS = 6


def _normalize_tag(tag):
    return " ".join(tag.strip().lower().split())


def cluster_by_weakness(students):
    """Group students by their most common shared weakness tag.

    `students` is a list of {id, name, weaknesses, risk_level, avg_grade}.
    Returns an ordered list of (topic, [student, ...]). Students with nothing
    recorded are collected under a single "de evaluat" topic so they stay
    visible on the board rather than silently vanishing.
    """
    tag_to_students = {}
    untagged = []

    for student in students:
        tags = [
            _normalize_tag(t)
            for t in (student.get("weaknesses") or "").split(",")
        ]
        tags = [t for t in tags if t not in _STOPWORD_TAGS]
        if not tags:
            untagged.append(student)
            continue
        for tag in tags:
            tag_to_students.setdefault(tag, []).append(student)

    # Most-shared weaknesses first, so the biggest real problem becomes a group.
    ordered = sorted(tag_to_students.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    clusters = []
    placed = set()
    for tag, members in ordered:
        remaining = [m for m in members if m["id"] not in placed]
        if not remaining:
            continue
        if len(clusters) >= _MAX_GROUPS:
            break
        clusters.append((tag, remaining))
        placed.update(m["id"] for m in remaining)

    # Anyone left over (weakness only shared beyond the group cap) plus the
    # students with no weakness recorded yet.
    leftovers = [s for s in students if s["id"] not in placed and s not in untagged]
    if leftovers:
        if clusters:
            clusters[-1][1].extend(leftovers)
        else:
            clusters.append(("diverse", leftovers))

    if untagged:
        clusters.append(("de evaluat", untagged))

    return clusters


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


def _demo_test_records(student, avg_grade, trend):
    """Turn a demo student's stated average + trend into real test records.

    The demo data used to be written straight into the metrics columns, which
    is why those columns never moved. Now it enters as the same evidence a
    teacher would type in, and recompute_metrics() derives the row from it.
    """
    topics = [t.strip() for t in (student.get("weaknesses") or "").split(",") if t.strip()]
    topics = topics or ["Recapitulare"]

    # Spread three results around the stated average in the stated direction.
    offsets = {"up": (-0.6, 0.0, 0.6), "down": (0.6, 0.0, -0.6)}.get(trend, (-0.2, 0.0, 0.2))
    grades = [max(1.0, min(MAX_GRADE, round(avg_grade + offset, 1))) for offset in offsets]

    records = []
    for index, grade in enumerate(grades):
        topic = topics[index % len(topics)]
        tags = [topic.lower()] if grade < 6 else []
        records.append({
            "grade": grade,
            "lessons": topic,
            "minutes_per_exercise": student.get("minutes_per_ex"),
            "mistake_tags": tags,
        })
    return records


def _seed_class(db, teacher_id, class_name, students):
    school_class = Class(name=class_name, teacher_id=teacher_id)
    db.add(school_class)
    db.flush()

    for s in students:
        student = Student(class_id=school_class.id, name=s["name"])
        db.add(student)
        db.flush()
        sid = student.id

        db.add(Profile(
            student_id=sid,
            strengths=s["strengths"],
            weaknesses=s["weaknesses"],
            learning_style=s["learning_style"],
            confidence=s["confidence"],
            personality_traits=s.get("personality") or "De evaluat",
            attention_span=s.get("attention_span") or "De evaluat",
            absent_lessons=s.get("absent_lessons") or "Fără absențe înregistrate",
        ))

        base_time = s.get("avg_time") or ""
        minutes = None
        if base_time:
            digits = "".join(ch for ch in base_time if ch.isdigit() or ch == ".")
            minutes = float(digits) if digits else None

        for record in _demo_test_records(dict(s, minutes_per_ex=minutes), s["avg_grade"], s["trend"]):
            db.add(TestRecord(
                student_id=sid,
                grade=record["grade"],
                lessons=record["lessons"],
                minutes_per_exercise=record["minutes_per_exercise"],
                mistake_tags_json=json.dumps(record["mistake_tags"], ensure_ascii=False),
                ai_insights=None,
            ))

        db.flush()
        recompute_metrics(db, sid, attendance=s["attendance"])

        # Demo students get the deterministic write-up, not 20 AI calls on the
        # first page load. The hand-written narratives that exist are kept.
        if "why" in s:
            db.add(AiInsight(
                student_id=sid,
                why_struggling=s["why"],
                recommended_actions_json=json.dumps(s["actions"], ensure_ascii=False),
            ))
        else:
            analysis = _fallback_profile(s["name"], db.get(Metric, sid), db.get(Profile, sid))
            analysis["strengths"] = s["strengths"]
            analysis["weaknesses"] = s["weaknesses"]
            analysis["learning_style"] = s["learning_style"]
            analysis["confidence"] = s["confidence"]
            _apply_analysis(db, sid, analysis)

    db.flush()
    _rebuild_groups(db, school_class.id)
    db.commit()


def load_demo_data(db, teacher_id):
    """Create the demo classes. Explicit: a real teacher's account must never
    silently fill up with invented students and invented grades, so this only
    runs when they press "încarcă date demo" on the empty state."""
    existing = db.scalars(
        select(Class.id).where(Class.teacher_id == teacher_id).limit(1)
    ).first()

    if existing:
        return False

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

    return True


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
        if selected_class is None:
            # An id the teacher does not own, or one that no longer exists.
            # Falling back to their first class here would quietly show a
            # different roster than the URL names, so say so instead.
            return classes, None, [], None
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

def elevi_page(db, apology, class_id=None):
    teacher_id = session["user_id"]

    classes, selected_class, students, extra = _risk_overview_data(db, teacher_id, class_id)
    if not classes:
        return render_template("clasa/elevi.html", classes=[], selected_class=None, students=[])

    if extra is None:
        return apology("Clasă inexistentă", 404)

    return render_template("clasa/elevi.html", classes=classes, selected_class=selected_class,
                           students=students, **extra)


def serve_upload(db, apology, filename):
    """Serve an uploaded test/solution page, but only to the teacher who owns
    the student it belongs to. Without this the files were written to disk and
    then unreachable - the teacher could never look at what they uploaded."""
    safe_name = os.path.basename(filename)

    owned = db.scalars(
        select(TestRecord.id)
        .join(Student, Student.id == TestRecord.student_id)
        .join(Class, Class.id == Student.class_id)
        .where(
            Class.teacher_id == session["user_id"],
            or_(
                TestRecord.test_filename == safe_name,
                TestRecord.solution_filename == safe_name,
            ),
        )
        .limit(1)
    ).first()

    if not owned:
        return apology("Fișier inexistent", 404)

    path = upload_path(safe_name)
    if not os.path.exists(path):
        return apology("Fișier inexistent", 404)

    return send_file(path)


def seed_demo(db):
    """POST target for the "load demo data" button on the empty state."""
    load_demo_data(db, session["user_id"])
    return redirect("/elevi")


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

    attendance = request.form.get("attendance", type=int)
    attendance = 80 if attendance is None else attendance
    absent_lessons = request.form.get("absent_lessons", "").strip() or "Fără absențe înregistrate"
    personality_traits = request.form.get("personality_traits", "").strip() or "De evaluat"
    attention_span = request.form.get("attention_span", "").strip() or "De evaluat"
    weaknesses_hint = request.form.get("weaknesses", "").strip()

    student = Student(class_id=target_class_id, name=name)
    db.add(student)
    db.flush()
    sid = student.id

    db.add(Profile(
        student_id=sid, strengths="De evaluat",
        weaknesses=weaknesses_hint or "De evaluat",
        learning_style="De evaluat", confidence="Medie",
        personality_traits=personality_traits, attention_span=attention_span,
        absent_lessons=absent_lessons,
    ))

    # Every grade/lesson row the form submitted, not just the first one - the
    # "+ adaugă notă" button and the live preview both count all of them.
    grades = request.form.getlist("grades[]")
    lessons = request.form.getlist("lessons[]")
    minutes = request.form.getlist("minutes[]")

    rows = []
    for index, (grade_text, lesson_text) in enumerate(zip(grades, lessons)):
        grade_text, lesson_text = grade_text.strip(), lesson_text.strip()
        if not grade_text and not lesson_text:
            continue
        rows.append({
            "grade": _to_grade(grade_text),
            "lessons": lesson_text or None,
            "minutes": _to_grade(minutes[index]) if index < len(minutes) else None,
        })

    test_filename = _save_upload(request.files.get("test_file"))
    solution_filename = _save_upload(request.files.get("solution_file"))

    # The uploaded pages attach to the first result; a review of the paper is
    # only meaningful against the grade it was given.
    for position, row in enumerate(rows):
        attach = position == 0
        _record_result(
            db, sid, name,
            grade=row["grade"], lessons=row["lessons"], minutes=row["minutes"],
            test_filename=test_filename if attach else None,
            solution_filename=solution_filename if attach else None,
        )

    if not rows and (test_filename or solution_filename):
        _record_result(
            db, sid, name, grade=None, lessons=None, minutes=None,
            test_filename=test_filename, solution_filename=solution_filename,
        )

    db.flush()
    recompute_metrics(db, sid, attendance=attendance)
    db.flush()

    # Build the profile in the same step, so the student is added "fully in one
    # go" rather than starting as a placeholder.
    _apply_analysis(db, sid, analyze_student(db, sid, name))
    db.flush()
    recompute_metrics(db, sid, attendance=attendance)
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


def _record_result(db, sid, student_name, grade, lessons, minutes,
                   test_filename, solution_filename):
    """Store one result, reviewing the uploaded pages against it when present."""
    test_text = read_uploaded_document(test_filename)
    solution_text = read_uploaded_document(solution_filename)

    insight, tags, transcript, _ai = review_test(
        student_name, lessons, grade, test_text, solution_text
    )

    record = TestRecord(
        student_id=sid,
        grade=grade,
        lessons=lessons,
        minutes_per_exercise=minutes,
        test_filename=test_filename,
        solution_filename=solution_filename,
        ai_insights=insight,
        mistake_tags_json=json.dumps(tags, ensure_ascii=False) if tags else None,
        transcript=transcript or None,
    )
    db.add(record)
    return record


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
    """Re-derive the metrics row and re-run the AI profile on current evidence."""
    student = _owned_student(db, sid)
    if not student:
        return redirect(request.referrer or "/elevi")

    recompute_metrics(db, sid)
    db.flush()
    _apply_analysis(db, sid, analyze_student(db, sid, student.name))
    db.flush()
    recompute_metrics(db, sid)
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
        # Ticking an action feeds the completion figure, so the row is rebuilt.
        db.flush()
        recompute_metrics(db, sid)
        db.commit()

    return redirect(request.referrer or "/elevi")


def chat_message(db, apology, sid):
    student = _owned_student(db, sid)
    if not student:
        return apology("Elev inexistent", 404)

    message = request.form.get("message", "").strip()
    if message:
        db.add(ChatMessage(student_id=sid, role="teacher", content=message))

        # Same engine as Mode 1 (secondary.ai.assistant), but handed this
        # student's real record plus the recent turns of this conversation so
        # the answers are about them rather than generic teaching advice.
        history = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.student_id == sid)
            .order_by(ChatMessage.id.desc())
            .limit(8)
        ).all()
        transcript = "\n".join(
            f"{'Profesor' if m.role == 'teacher' else 'Asistent'}: {m.content}"
            for m in reversed(history)
        )

        context = (
            "Ești un asistent AI care ajută un profesor de matematică cu un elev anume.\n\n"
            f"{_evidence_summary(db, sid, student.name)}\n\n"
            + (f"Conversația până acum:\n{transcript}\n\n" if transcript else "")
            + f"Întrebarea profesorului: {message}\n\n"
            "Răspunde concret, în română, bazându-te pe datele de mai sus. Dacă îți lipsesc "
            "date pentru un răspuns bine fundamentat, spune ce ar trebui înregistrat în plus."
        )
        reply = ai.assistant(context)

        if ai.is_error(reply):
            # Don't leave the teacher's question hanging unanswered in the
            # thread, but don't store an error as if it were advice either.
            reply = (
                "Nu am putut genera un răspuns acum. " + str(reply)
                + "\n\nÎntrebarea ta a fost păstrată — încearcă din nou mai târziu."
            )

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
    "mode1": "Asistent predare (Mod 1)",
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
            # The model test is only useful as content - passing the filename
            # alone told the model nothing about what to imitate.
            model_text = read_uploaded_document(filename)
            if model_text:
                parts.append(f"Testul-model încărcat conține:\n{model_text[:6000]}\n")
            else:
                parts.append(f"Model încărcat ({filename}), dar conținutul nu a putut fi citit.")
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
            sheet_text = read_uploaded_document(filename)
            if sheet_text:
                parts.append(f"Fișa scrisă de mână transcrisă:\n{sheet_text[:6000]}\n")
            else:
                parts.append(f"Fișă încărcată ({filename}), dar transcrierea nu a reușit.")
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


def _recurring_mistake_tags(db, sid, minimum=1):
    """Error tags from this student's reviewed papers, most frequent first."""
    rows = db.scalars(
        select(TestRecord.mistake_tags_json).where(TestRecord.student_id == sid)
    ).all()
    counter = Counter()
    for raw in rows:
        if not raw:
            continue
        try:
            for tag in json.loads(raw):
                tag = str(tag).strip()
                if tag:
                    counter[tag] += 1
        except (ValueError, TypeError):
            continue
    return [tag for tag, count in counter.most_common(6) if count >= minimum]


def _render_worksheet(prompt):
    """Generate a worksheet, or say plainly that it could not be generated.

    ai.assistant() signals a dead key or exhausted quota by returning an
    "Eroare AI: ..." string. Rendering that onto the worksheet card would hand
    the teacher a printable page whose body is an error message, so it becomes
    a visible notice instead.
    """
    raw = ai.assistant(prompt)
    if ai.is_error(raw):
        return markdown.markdown(
            "**Fișa nu a putut fi generată.**\n\n"
            + str(raw)
            + "\n\nÎncearcă din nou după ce cheia AI este funcțională."
        )
    return markdown.markdown(raw)


def generate_exercises(db, apology, sid):
    student = _owned_student(db, sid)
    if not student:
        return apology("Elev inexistent", 404)

    profile = db.get(Profile, sid)
    difficulty = request.form.get("difficulty", "mediu")
    difficulty_desc = DIFFICULTY_PROMPTS.get(difficulty, DIFFICULTY_PROMPTS["mediu"])
    source_mode = request.form.get("source_mode", "mode1")
    source_mode_desc = SOURCE_MODE_PROMPTS.get(source_mode, SOURCE_MODE_PROMPTS["mode1"])
    weaknesses = (profile.weaknesses if profile else None) or "algebră generală"
    mode_fields_desc = _mode_specific_prompt_fragment(db, session["user_id"], source_mode)

    # The error tags the paper reviews actually found beat the free-text
    # weakness list, because they name the step the student gets wrong.
    mistake_tags = _recurring_mistake_tags(db, sid)
    targeted = ", ".join(mistake_tags) if mistake_tags else weaknesses

    prompt = (
        "Genereaza un set de 5 exerciții de matematică, numerotate, cu enunț clar, "
        f"axate pe următoarele dificultăți concrete ale elevului: {targeted}. "
        + (f"Puncte slabe generale notate în profil: {weaknesses}. " if mistake_tags else "")
        + f"Nivel de dificultate: {difficulty_desc}. "
        f"Stil de formulare: {source_mode_desc} "
        + (f"{mode_fields_desc} " if mode_fields_desc else "")
        + "Nu include rezolvările, doar enunțurile, pregătite pentru tipărire ca fișă de lucru."
    )

    worksheet = _render_worksheet(prompt)

    page = _render_student_page(
        db, student.class_id, sid,
        active_tab="exercitii", worksheet=worksheet, difficulty=difficulty, source_mode=source_mode,
    )
    if page is None:
        return apology("Elev sau clasă inexistentă", 404)
    return page


# ---------------------------------------------------------
# Mode 4 of 4 — Test & Assignment Review: upload the given
# test + the student's handwritten solution, get the paper
# transcribed and reviewed. Shared with the one-time Add
# Student flow via _record_result() above.
# ---------------------------------------------------------

def submit_test_review(db, apology, sid):
    student = _owned_student(db, sid)
    if not student:
        return apology("Elev inexistent", 404)

    grade = _to_grade(request.form.get("grade", "").strip() or None)
    lessons = request.form.get("lessons", "").strip() or None
    minutes = _to_grade(request.form.get("minutes_per_exercise", "").strip() or None)
    test_filename = _save_upload(request.files.get("test_file"))
    solution_filename = _save_upload(request.files.get("solution_file"))

    if grade is None and not lessons and not test_filename and not solution_filename:
        return apology("Adaugă o notă, o lecție sau o lucrare încărcată", 400)

    record = _record_result(
        db, sid, student.name,
        grade=grade, lessons=lessons, minutes=minutes,
        test_filename=test_filename, solution_filename=solution_filename,
    )
    db.flush()

    # A new result changes the evidence, so the risk row and the profile that
    # reads from it are both rebuilt rather than left at their old values.
    recompute_metrics(db, sid)
    db.flush()
    _apply_analysis(db, sid, analyze_student(db, sid, student.name))
    db.flush()
    recompute_metrics(db, sid)
    db.commit()

    page = _render_student_page(
        db, student.class_id, sid, active_tab="recenzie", test_insight=record.ai_insights,
    )
    if page is None:
        return apology("Elev sau clasă inexistentă", 404)
    return page


# ---------------------------------------------------------
# Screen C — Smart Groups board
# ---------------------------------------------------------

def _class_roster_for_grouping(db, class_id):
    """Each student in the class with the fields grouping decisions need."""
    rows = db.execute(
        select(Student.id, Student.name, Profile.weaknesses, Metric.risk_level, Metric.avg_grade)
        .outerjoin(Profile, Profile.student_id == Student.id)
        .outerjoin(Metric, Metric.student_id == Student.id)
        .where(Student.class_id == class_id)
        .order_by(Student.id.asc())
    ).mappings().all()
    return [dict(r) for r in rows]


def _rebuild_groups(db, class_id):
    """Re-cluster a class into groups built from what its students actually
    struggle with, replacing whatever groups were there before.

    This is what makes the board work for a class the teacher created: there
    are no pre-seeded buckets to fall into, so the groups are derived - named
    and described by AI when it is reachable, by the topic itself when not.
    """
    students = _class_roster_for_grouping(db, class_id)
    if not students:
        return []

    clusters = cluster_by_weakness(students)

    db.execute(
        delete(GroupMember).where(
            GroupMember.group_id.in_(select(Group.id).where(Group.class_id == class_id))
        )
    )
    db.execute(delete(Group).where(Group.class_id == class_id))
    db.flush()

    analyzed = analyze_groups(clusters)

    created = []
    for topic, members in clusters:
        name, description, actions = analyzed[topic]
        group = Group(
            class_id=class_id,
            name=name,
            weakness_tag=topic,
            description=description,
            suggested_actions_json=json.dumps(
                [{"text": text, "done": False} for text in actions], ensure_ascii=False
            ),
        )
        db.add(group)
        db.flush()
        for member in members:
            db.add(GroupMember(group_id=group.id, student_id=member["id"]))
        created.append(group)

    return created


def groups_page(db, apology, class_id):
    teacher_id = session["user_id"]
    classes = _teacher_classes(db, teacher_id)
    selected_class = next((c for c in classes if c.id == class_id), None)
    if not selected_class:
        return apology("Clasă inexistentă", 404)

    groups = db.scalars(
        select(Group).where(Group.class_id == class_id).order_by(Group.id.asc())
    ).all()

    # First visit to a class that has students but no groups yet: build them,
    # rather than showing an empty board with a button that used to do nothing.
    if not groups and _class_roster_for_grouping(db, class_id):
        groups = _rebuild_groups(db, class_id)
        db.commit()

    board = []
    for g in groups:
        members = db.execute(
            select(Student.id, Student.name, Metric.risk_level)
            .join(GroupMember, GroupMember.student_id == Student.id)
            .outerjoin(Metric, Metric.student_id == Student.id)
            .where(GroupMember.group_id == g.id)
            .order_by(Student.name.asc())
        ).mappings().all()
        board.append({"group": g, "members": members})

    unassigned = db.execute(
        select(Student.id, Student.name, Metric.risk_level)
        .outerjoin(Metric, Metric.student_id == Student.id)
        .where(
            Student.class_id == class_id,
            Student.id.not_in(select(GroupMember.student_id)),
        )
        .order_by(Student.name.asc())
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
    """Re-cluster the class from scratch on the current weakness data."""
    if not _owned_class(db, session["user_id"], class_id):
        return apology("Clasă inexistentă", 404)

    _rebuild_groups(db, class_id)
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
        suggested_actions = _group_actions(db, group)
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


def _group_members_for_analysis(db, gid):
    rows = db.execute(
        select(Student.id, Student.name, Metric.risk_level, Metric.avg_grade, Profile.weaknesses)
        .join(GroupMember, GroupMember.student_id == Student.id)
        .outerjoin(Metric, Metric.student_id == Student.id)
        .outerjoin(Profile, Profile.student_id == Student.id)
        .where(GroupMember.group_id == gid)
        .order_by(Student.name.asc())
    ).mappings().all()
    return [dict(r) for r in rows]


def _group_actions(db, group):
    """Suggested actions for a group, generated from its real members."""
    members = _group_members_for_analysis(db, group.id)
    _name, description, actions, _ai = analyze_group(group.weakness_tag or group.name, members)
    if not group.description:
        group.description = description
    return [{"text": text, "done": False} for text in actions]


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

    members = _group_members_for_analysis(db, group.id)
    name, description, actions, _ai = analyze_group(group.weakness_tag or group.name, members)
    group.description = description
    if name:
        group.name = name
    group.suggested_actions_json = json.dumps(
        [{"text": text, "done": False} for text in actions], ensure_ascii=False
    )
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
        f"un grup de elevi ({member_names}) care au în comun dificultăți la: "
        f"{group.weakness_tag or group.name}. "
        f"Nivel de dificultate: {difficulty_desc}. "
        f"Stil de formulare: {source_mode_desc} "
        "Nu include rezolvările, doar enunțurile, pregătite pentru tipărire ca fișă de lucru comună grupei."
    )

    worksheet = _render_worksheet(prompt)

    return group_detail(db, apology, class_id, gid,
                        worksheet=worksheet, difficulty=difficulty, source_mode=source_mode)
