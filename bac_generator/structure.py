"""
The shape of a Romanian BAC maths paper, per profile, measured from 217
official papers (see tools/mine_bac_corpus.py).

Three things live here:

1. PROFILES - what each paper looks like. A real paper is 18 items worth 5p
   each (90p + 10p din oficiu = 100p). M1, M2 and M_tehnologic share one shape;
   M_pedagogic is a genuinely different paper and gets its own.
2. Slot topics - derived from the mined blueprint rather than hand-written,
   because the hand-written map this replaces was measurably wrong (it put
   Numere complexe / Trigonometrie at Subiect I item 5, where 100% of real
   M_tehnologic papers have Geometrie analitică).
3. split_subpoints() - turns the "a) ... b) ... c) ..." blob that the existing
   Subiect II/III templates already emit into three separately-marked
   subpoints, so no template had to be rewritten.
"""

import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ─────────────────────────────── profiles ───────────────────────────────

SUBJECT_NAMES = {1: "SUBIECTUL I", 2: "SUBIECTUL al II-lea", 3: "SUBIECTUL al III-lea"}
POINTS_PER_ITEM = 5
OFFICIAL_BONUS = 10          # "se acordă 10 puncte din oficiu"

# kind:
#   "items"    - N standalone one-mark items (Subiect I everywhere)
#   "problems" - N problems, each a stem plus labelled subpoints
#   "tema"     - one stem explored over N numbered items (M_pedagogic II / III)
_STANDARD_SUBJECTS = [
    {"subject": 1, "kind": "items",    "count": 6, "slots": ["I.1", "I.2", "I.3", "I.4", "I.5", "I.6"]},
    {"subject": 2, "kind": "problems", "count": 2, "slots": ["II.p1", "II.p2"],  "subpoints": ["a", "b", "c"]},
    {"subject": 3, "kind": "problems", "count": 2, "slots": ["III.p1", "III.p2"], "subpoints": ["a", "b", "c"]},
]

_PEDAGOGIC_SUBJECTS = [
    {"subject": 1, "kind": "items", "count": 6, "slots": ["I.1", "I.2", "I.3", "I.4", "I.5", "I.6"]},
    {"subject": 2, "kind": "tema",  "count": 6, "slots": ["II.tema"]},
    {"subject": 3, "kind": "tema",  "count": 6, "slots": ["III.tema"]},
]

PROFILES = {
    "M1": {
        "code": "M1",
        "title": "Matematică M_mate-info",
        "label": "M_mate-info",
        "filiera": [
            "Filiera teoretică, profilul real, specializarea matematică-informatică",
            "Filiera vocațională, profilul militar, specializarea matematică-informatică",
        ],
        "subjects": _STANDARD_SUBJECTS,
    },
    "M2": {
        "code": "M2",
        "title": "Matematică M_șt-nat",
        "label": "M_șt-nat",
        "filiera": [
            "Filiera teoretică, profilul real, specializarea științe ale naturii",
        ],
        "subjects": _STANDARD_SUBJECTS,
    },
    "M3": {
        "code": "M3",
        "title": "Matematică M_tehnologic",
        "label": "M_tehnologic",
        "filiera": [
            "Filiera tehnologică: profilul servicii, toate calificările profesionale; "
            "profilul resurse naturale și protecția mediului, toate calificările profesionale; "
            "profilul tehnic, toate calificările profesionale",
        ],
        "subjects": _STANDARD_SUBJECTS,
    },
    "M_PED": {
        "code": "M_PED",
        "title": "Matematică M_pedagogic",
        "label": "M_pedagogic",
        "filiera": [
            "Filiera vocațională, profilul pedagogic, specializarea învățător-educatoare",
        ],
        "subjects": _PEDAGOGIC_SUBJECTS,
        # Measured over 49 papers: the pedagogic programme contains no analysis.
        "excluded_lessons": ["Derivate", "Limite", "Integrale definite"],
    },
}

DEFAULT_PROFILE = "M3"

# `get_spec_details()` has always called the pedagogic profile "M4", and
# Conversation.bac rows in the database may hold any of these spellings.
PROFILE_ALIASES = {
    None: DEFAULT_PROFILE, "": DEFAULT_PROFILE,
    "M4": "M_PED", "M_PEDAGOGIC": "M_PED", "M3_PEDA": "M_PED", "PEDAGOGIC": "M_PED",
    "M3_TEH": "M3", "M_TEHNOLOGIC": "M3", "TEHNOLOGIC": "M3",
    "M_MATE-INFO": "M1", "MATE-INFO": "M1",
    "M_ST-NAT": "M2", "ST-NAT": "M2",
}


def resolve_profile(code):
    """Normalise anything that might be sitting in Conversation.bac."""
    if code in PROFILES:
        return code
    key = str(code).strip().upper() if code is not None else None
    if key in PROFILES:
        return key
    return PROFILE_ALIASES.get(key, DEFAULT_PROFILE)


def profile_spec(code):
    return PROFILES[resolve_profile(code)]


def slots_for(code):
    """Every slot key of a profile's paper, in printed order."""
    return [slot for subject in profile_spec(code)["subjects"] for slot in subject["slots"]]


def subject_of(code, slot):
    for subject in profile_spec(code)["subjects"]:
        if slot in subject["slots"]:
            return subject
    return None


def total_points(code):
    """What the paper is worth before the 10 points din oficiu."""
    total = 0
    for subject in profile_spec(code)["subjects"]:
        if subject["kind"] == "problems":
            total += subject["count"] * len(subject["subpoints"]) * POINTS_PER_ITEM
        else:
            total += subject["count"] * POINTS_PER_ITEM
    return total


# ───────────────────── registry bridge (keeps 70 templates) ─────────────────────

# The registry is keyed by the original integer slots 1-10. Mapping the new slot
# keys back onto them means every existing template keeps working untouched.
LEGACY_SLOT = {
    "I.1": 1, "I.2": 2, "I.3": 3, "I.4": 4, "I.5": 5, "I.6": 6,
    "II.p1": 7, "II.p2": 8, "III.p1": 9, "III.p2": 10,
    # M_pedagogic reuses the same maths from a different shape: its Subiect II
    # is a composition law (slot 8) and its Subiect III a matrix pair (slot 7).
    # The templates there emit a/b/c triples, not six items, so coverage.py
    # reports these as reused-not-native until dedicated families exist.
    "II.tema": 8, "III.tema": 7,
}

NATIVE_TEMA_SLOTS = frozenset()   # nothing emits the pedagogic six-item shape yet


def legacy_slot(slot):
    return LEGACY_SLOT[slot]


# ─────────────────────────────── blueprint ───────────────────────────────

_BLUEPRINT = None


def blueprint():
    """The mined topic distribution. Loaded lazily, from a path derived from
    __file__ so it does not depend on the working directory."""
    global _BLUEPRINT
    if _BLUEPRINT is None:
        path = os.path.join(DATA_DIR, "blueprint.json")
        try:
            with open(path, encoding="utf-8") as handle:
                _BLUEPRINT = json.load(handle)
        except (OSError, ValueError):
            _BLUEPRINT = {"profiles": {}}
    return _BLUEPRINT


# Blueprint topics are the miner's vocabulary; lesson names are the UI's. They
# are deliberately kept identical, so this map only has to cover the exceptions.
TOPIC_TO_LESSON = {}

# "Ecuații" is how the corpus describes Subiect I item 3, but "solve an
# equation" is a task, not a chapter - the real papers there are radical,
# exponential, logarithmic or quadratic equations, and our templates are
# already tagged with those. Keeping it as a weight would make the slot ask
# for a lesson no template can ever supply.
DESCRIPTOR_TOPICS = frozenset({"Ecuații"})


def slot_weights(code, slot):
    """{lesson: share} for one slot, measured from the corpus."""
    profile = resolve_profile(code)
    entry = blueprint().get("profiles", {}).get(profile, {}).get("slots", {}).get(slot)
    if not entry:
        return {}
    excluded = set(profile_spec(profile).get("excluded_lessons", ()))
    weights = {}
    for topic, share in entry.get("topics", {}).items():
        if topic in DESCRIPTOR_TOPICS:
            continue
        lesson = TOPIC_TO_LESSON.get(topic, topic)
        if lesson not in excluded:
            weights[lesson] = weights.get(lesson, 0.0) + share
    return weights


def slot_lessons(code, slot):
    """Lessons a slot may draw from, most frequent first."""
    return [lesson for lesson, _ in
            sorted(slot_weights(code, slot).items(), key=lambda kv: -kv[1])]


def forced_lessons(code, omitted_lessons):
    """Lessons that appear however hard the teacher tries to omit them.

    The official structure fixes what each slot is about, so a slot whose every
    lesson has been omitted still has to produce one of them - handing back a
    paper that is a subject short would be worse.
    """
    omitted = set(omitted_lessons or ())
    forced = set()
    for slot in slots_for(code):
        lessons = slot_lessons(code, slot)
        if lessons and omitted.issuperset(lessons):
            forced.update(lessons)
    return sorted(forced)


# Back-compat: bac_generator/routes.py imports SLOT_LESSONS and ships it to the
# mode5 lesson picker, which warns about omissions it cannot honour. Keeping the
# 1-10 integer shape means that JS needs no change.
def _legacy_slot_lessons():
    return {
        number: slot_lessons(DEFAULT_PROFILE, slot)
        for slot, number in LEGACY_SLOT.items()
        if slot in slots_for(DEFAULT_PROFILE)
    }


class _LazySlotLessons(dict):
    """Populates itself from the blueprint on first access."""

    def _fill(self):
        if not super().__len__():
            super().update(_legacy_slot_lessons())
        return self

    def __getitem__(self, key):
        return dict.__getitem__(self._fill(), key)

    def get(self, key, default=None):
        return dict.get(self._fill(), key, default)

    def values(self):
        return dict.values(self._fill())

    def items(self):
        return dict.items(self._fill())

    def keys(self):
        return dict.keys(self._fill())

    def __iter__(self):
        return dict.__iter__(self._fill())

    def __len__(self):
        return dict.__len__(self._fill())


SLOT_LESSONS = _LazySlotLessons()


# ───────────────────────────── subpoint adapter ─────────────────────────────

# Matches "a)" / "b)" / "c)" at the start of a line or after a blank line. This
# is the same convention validators/verify.py:_strip_list_markers already uses,
# and all 23 Subiect II/III templates were verified to follow it.
_SUBPOINT_RE = re.compile(r"(?:\A|\n\s*\n)\s*([a-d])\)\s*", re.M)


def split_subpoints(text):
    """("stem", [("a", body), ("b", body), ...]) from an a)/b)/c) blob.

    Returns (text, []) when the text has no subpoints, so callers can treat a
    plain Subiect I item and a Subiect II problem the same way.
    """
    if not text:
        return "", []

    matches = list(_SUBPOINT_RE.finditer(text))
    if not matches:
        return text.strip(), []

    stem = text[: matches[0].start()].strip()
    parts = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end(): end].strip()
        if body:
            parts.append((match.group(1), body))
    return stem, parts


def build_units(exercise, subject, points_each=POINTS_PER_ITEM):
    """The separately-marked pieces one generated exercise contributes.

    A Subiect I item is one unit. A Subiect II/III problem is one unit per
    subpoint, which is what makes a generated paper add up to 90 points the way
    a real one does. If a problem's text cannot be split into the subpoints its
    subject expects, it stays a single unit carrying the whole mark and is
    flagged - degrading visibly beats mangling the statement.
    """
    kind = subject["kind"]
    expected = subject.get("subpoints") or []

    if kind == "items":
        return [{
            "label": None,
            "text": exercise.get("text", ""),
            "solution": exercise.get("solution", ""),
            "points": points_each,
        }], None

    stem, parts = split_subpoints(exercise.get("text", ""))
    _, solution_parts = split_subpoints(exercise.get("solution", ""))
    solutions = dict(solution_parts)

    if expected and [label for label, _ in parts] != list(expected):
        return [{
            "label": None,
            "text": exercise.get("text", ""),
            "solution": exercise.get("solution", ""),
            "points": points_each * max(len(expected), 1),
        }], "subpoint_split_failed"

    units = [{
        "label": label,
        "text": body,
        "solution": solutions.get(label, ""),
        "points": points_each,
    } for label, body in parts]

    return units, (None if units else "no_subpoints")
