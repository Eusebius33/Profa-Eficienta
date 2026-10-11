"""
Practice exercise generator.

The BAC generator assembles a whole paper: fixed slots, fixed structure, one
exercise each. This serves the other half of the job -- a teacher who wants
*n* exercises on the chapters they pick, at the difficulty they pick, with the
worked solution available per exercise.

It reuses the same 70-odd templates in `generators/`, so nothing here invents
mathematics; it only chooses which templates to draw from and how many times.

Determinism: a run is fully described by (profile, chapters, difficulty, count,
seed). The same five values always rebuild the same set, which is what makes
the seed worth showing to the teacher.
"""
import hashlib
import random
import re

from bac_generator import structure
from bac_generator.generators import registry
from bac_generator.generators import difficulty as difficulty_mod


# Every registered template declares a `topic`. Chapters group those topics the
# way a teacher thinks about the syllabus, which is coarser than the template
# names. `lessons` ties a chapter to the blueprint lesson names so a chapter can
# be hidden for a profile that never examines it (a pedagogic paper has no
# derivatives, so offering that chapter would only produce an empty set).
CHAPTERS = [
    {
        "slug": "puteri-radicali",
        "label": "Puteri și radicali",
        "match": ("radical", "puteri"),
        "lessons": ("Radicali", "Puteri"),
    },
    {
        "slug": "logaritmi",
        "label": "Logaritmi",
        "match": ("logaritm",),
        "lessons": ("Logaritmi",),
    },
    {
        "slug": "functii",
        "label": "Funcții",
        "match": ("funcți", "grafic", "domeniu", "codomeniu", "monotonie", "zero-produs"),
        "lessons": ("Funcții",),
    },
    {
        "slug": "ecuatii",
        "label": "Ecuații în ℝ",
        "match": ("ecuații", "ecuație", "ecuația", "fracțiilor algebrice", "discriminant"),
        "lessons": ("Ecuații", "Funcții"),
    },
    {
        "slug": "numere-complexe",
        "label": "Numere complexe",
        "match": ("complex",),
        "lessons": ("Numere complexe",),
    },
    {
        "slug": "polinoame",
        "label": "Polinoame",
        "match": ("polinoam", "teorema restului", "viète", "divizibilitat"),
        "lessons": ("Polinoame",),
    },
    {
        "slug": "matrice",
        "label": "Matrice și determinanți",
        "match": ("matric", "determinant"),
        "lessons": ("Matrici",),
    },
    {
        "slug": "sisteme",
        "label": "Sisteme de ecuații liniare",
        "match": ("sisteme",),
        "lessons": ("Matrici",),
    },
    {
        "slug": "structuri",
        "label": "Structuri algebrice",
        "match": ("legi de compoziție",),
        "lessons": ("Legi de compoziție",),
    },
    {
        "slug": "siruri",
        "label": "Șiruri",
        "match": ("inducție", "șir"),
        "lessons": ("Progresii",),
    },
    {
        "slug": "limite",
        "label": "Limite de funcții",
        "match": ("limit", "continuitat"),
        "lessons": ("Limite",),
    },
    {
        "slug": "derivate",
        "label": "Derivate",
        "match": ("derivat", "tangenta", "convexitat"),
        "lessons": ("Derivate",),
    },
    {
        "slug": "integrale",
        "label": "Primitive și integrale",
        "match": ("integral", "primitiv", "aria suprafeței", "curbe"),
        "lessons": ("Integrale definite",),
    },
    {
        "slug": "geometrie",
        "label": "Geometrie plană și analitică",
        "match": ("geometrie", "dreapt", "drept", "coliniaritat", "segment", "distanța",
                  "teorema cosinusului", "teorema sinusurilor", "vector", "triunghi"),
        "lessons": ("Geometrie analitică", "Geometrie plană"),
    },
    {
        "slug": "trigonometrie",
        "label": "Trigonometrie",
        "match": ("trigonometri",),
        "lessons": ("Trigonometrie",),
    },
    {
        "slug": "combinatorica",
        "label": "Combinatorică și probabilități",
        "match": ("probabilitat", "combinări", "aranjamente", "permutări",
                  "numărare", "binomial"),
        "lessons": ("Probabilități",),
    },
    {
        "slug": "progresii",
        "label": "Progresii",
        "match": ("progresii",),
        "lessons": ("Progresii",),
    },
    {
        "slug": "procente",
        "label": "Procente și aplicații",
        "match": ("procent",),
        "lessons": ("Procente",),
    },
]

# CHAPTERS is in the order the form shows them. Matching has to run
# specific-before-general instead, or "Sisteme de ecuații liniare cu matrice"
# lands in Ecuații and "Integrale definite - polinoame" lands in Polinoame.
MATCH_ORDER = (
    "sisteme", "structuri", "integrale", "derivate", "limite",
    "trigonometrie", "combinatorica", "numere-complexe", "progresii",
    "siruri", "procente", "matrice", "polinoame", "logaritmi",
    "puteri-radicali", "geometrie", "ecuatii", "functii",
)

CHAPTERS_BY_SLUG = {c["slug"]: c for c in CHAPTERS}

PROFILES = [
    {"code": "M1", "label": "Mate-Info"},
    {"code": "M2", "label": "Științele Naturii"},
    {"code": "M3", "label": "Tehnologic"},
    {"code": "M_PED", "label": "Pedagogic"},
]

# Olimpic is deliberately absent: this is BAC practice, and the generator's own
# note says nothing above the syllabus belongs in a BAC-shaped set.
LEVELS = [
    {"code": "usor", "label": "Ușor"},
    {"code": "mediu", "label": "Mediu"},
    {"code": "dificil", "label": "Dificil"},
]

MIN_COUNT, MAX_COUNT, DEFAULT_COUNT = 1, 30, 10


def _chapter_for_topic(topic):
    """The chapter a template's topic belongs to, or None."""
    low = (topic or "").lower()
    for slug in MATCH_ORDER:
        chapter = CHAPTERS_BY_SLUG[slug]
        if any(bad in low for bad in chapter.get("exclude", ())):
            continue
        if any(needle in low for needle in chapter["match"]):
            return slug
    return None


def _all_templates():
    """Every registered template once, with its chapter resolved."""
    seen, out = set(), []
    for slot, funcs in registry.slots.items():
        for func in funcs:
            key = getattr(func, "template_id", None) or id(func)
            if key in seen:
                continue
            seen.add(key)
            chapter = _chapter_for_topic(getattr(func, "topic", ""))
            if chapter:
                out.append((chapter, slot, func))
    return out


# Resolved once at import: the registry is populated by decorators at module
# import and never changes afterwards.
_TEMPLATES = _all_templates()


def chapters_for(profile=None, level=None):
    """Chapters that can actually produce an exercise for this profile/level.

    The UI greys out the rest rather than offering a choice that would come
    back empty.
    """
    profile = structure.resolve_profile(profile)
    level = difficulty_mod.normalize_level(level)
    allowed_lessons = {
        lesson
        for slot in structure.slots_for(profile)
        for lesson in structure.slot_lessons(profile, slot)
    }

    out = []
    for chapter in CHAPTERS:
        in_profile = bool(set(chapter["lessons"]) & allowed_lessons)
        pool = [
            func for slug, _slot, func in _TEMPLATES
            if slug == chapter["slug"] and level in difficulty_mod.template_bands(func)
        ]
        out.append({
            "slug": chapter["slug"],
            "label": chapter["label"],
            "available": bool(in_profile and pool),
            "templates": len(pool),
        })
    return out


def _pool(chapter_slugs, level):
    """Templates to draw from, honouring the chapter picks and the level.

    Falls back to every template of the chosen chapters when the level filter
    would empty the pool -- an off-level exercise beats no exercise, and the
    exercise reports its own band so the card can say so.
    """
    wanted = set(chapter_slugs or [])
    chosen = [(slug, func) for slug, _slot, func in _TEMPLATES
              if not wanted or slug in wanted]
    at_level = [(slug, f) for slug, f in chosen
                if level in difficulty_mod.template_bands(f)]
    return at_level or chosen


def normalize_seed(seed):
    """A short, readable, reproducible seed. Blank means 'pick one for me'."""
    seed = (seed or "").strip()
    if not seed:
        return "%06x" % random.getrandbits(24)
    # Keep it to something a teacher can retype off the screen.
    cleaned = re.sub(r"[^0-9a-zA-Z._-]", "", seed)[:32]
    return cleaned or hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]


def _split_solution(solution):
    """The worked solution as discrete steps.

    Templates write their solutions as newline-separated lines of reasoning,
    which is exactly the granularity the step panel wants.
    """
    lines = [ln.strip() for ln in (solution or "").split("\n")]
    return [ln for ln in lines if ln]


def generate(profile=None, chapters=None, level=None, count=DEFAULT_COUNT, seed=None):
    """Build a practice set.

    Returns {"seed", "profile", "difficulty", "chapters", "exercises"} where
    each exercise carries its statement, final answer, worked steps and the
    chapter/difficulty badges the card shows.
    """
    profile = structure.resolve_profile(profile)
    level = difficulty_mod.normalize_level(level)
    seed = normalize_seed(seed)
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = DEFAULT_COUNT
    count = max(MIN_COUNT, min(count, MAX_COUNT))

    # Only chapters this profile actually examines, at a level that has
    # templates for them. The form greys the rest out; this makes the API
    # agree with it instead of quietly generating off-profile work.
    allowed = {c["slug"] for c in chapters_for(profile, level) if c["available"]}
    chapters = sorted(set(chapters or allowed) & allowed)

    pool = _pool(chapters, level) if chapters else []
    if not pool:
        return {
            "seed": seed, "profile": profile, "difficulty": level,
            "chapters": list(chapters or []), "exercises": [],
        }

    rng = random.Random(f"{profile}|{level}|{','.join(sorted(chapters or []))}|{seed}")
    biased = difficulty_mod.wrap(rng, level)

    # Spread the draw across the chosen chapters instead of letting the biggest
    # chapter dominate: walk the chapters in turn, taking one template from each
    # before coming back round.
    by_chapter = {}
    for slug, func in pool:
        by_chapter.setdefault(slug, []).append(func)
    order = sorted(by_chapter)
    rng.shuffle(order)

    exercises = []
    cursor = 0
    while len(exercises) < count:
        slug = order[cursor % len(order)]
        cursor += 1
        func = rng.choice(by_chapter[slug])
        try:
            raw = func(biased)
        except Exception:  # noqa: BLE001 - one bad draw must not kill the set
            continue

        steps = _split_solution(raw.get("solution"))
        exercises.append({
            "index": len(exercises) + 1,
            "chapter": slug,
            "chapter_label": CHAPTERS_BY_SLUG[slug]["label"],
            "topic": raw.get("topic") or "",
            "statement": raw.get("text") or "",
            # The concluding line is the answer; the whole working is the steps.
            "answer": steps[-1] if steps else "",
            "steps": steps,
            "points": raw.get("points", 5),
            "lesson": raw.get("lesson") or "",
            "template_id": raw.get("template_id") or "",
            "band": difficulty_mod.LEVEL_LABELS.get(level, level),
        })

    return {
        "seed": seed,
        "profile": profile,
        "difficulty": level,
        "chapters": sorted(set(chapters or [])),
        "exercises": exercises,
    }


def export_content(exercises, include_solutions=False):
    """Render selected exercises as the numbered text the exporters expect.

    `secondary.exports` splits a reply into items on leading numbers, so the
    worksheet comes out of the same pipeline the chat modes already use.
    """
    blocks = []
    for position, ex in enumerate(exercises, start=1):
        block = [f"{position}. {ex.get('statement', '').strip()}"]
        if include_solutions:
            steps = ex.get("steps") or []
            if steps:
                block.append("")
                block.append("**Rezolvare:**")
                block.extend(f"- {step}" for step in steps)
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)
