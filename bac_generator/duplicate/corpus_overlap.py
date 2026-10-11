"""
Check a generated statement against the 217 official papers.

WHAT THIS CAN AND CANNOT DO
---------------------------
The corpus fingerprints are built from text extracted out of the official PDFs,
and that extraction loses the radical sign entirely and most integral signs
(see tools/mine_bac_corpus.py). So the exact and template+params hashes the
rest of duplicate/ relies on can never collide with a generated exercise - the
two sides are not even written in the same notation. Seeding those levels with
corpus data would look like protection while doing nothing.

What does survive glyph loss is vocabulary. "Determinați ecuația dreptei care
trece prin punctele" reads the same whether or not a square root rendered. So
the one honest corpus check is token overlap, scoped to the slot the exercise
is being generated for, which is both cheap (~57 papers per slot) and
meaningful.

It REPORTS rather than rejects. With only five templates at Subiect I item 5
and Geometrie analitică in 100% of real papers there, a strict threshold would
make that slot unfillable. The score rides along in exam metadata so the
threshold can be set from measured data instead of guessed at.
"""

import json
import os
import re
import unicodedata
from functools import lru_cache

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "official_fingerprints.json",
)

# Mirrors the miner's stopword list; these words carry no discriminating
# signal because every BAC statement contains them.
STOPWORDS = {
    "care", "sunt", "este", "pentru", "orice", "unde", "intr", "intre", "din", "dintre",
    "cu", "si", "sau", "in", "la", "de", "al", "ale", "un", "se", "ca", "ce",
    "numarul", "numerele", "numar", "real", "reale", "naturale", "multimea", "consider",
    "considera", "aratati", "determinati", "calculati", "demonstrati", "rezolvati",
}


def _fold(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def tokens_of(text):
    """The content words of a statement, LaTeX markup stripped first."""
    text = re.sub(r"\$[^$]*\$", " ", str(text or ""))      # drop inline maths
    text = re.sub(r"\\[a-zA-Z]+", " ", text)               # drop stray commands
    words = re.findall(r"[a-z]{4,}", _fold(text))
    return {w for w in words if w not in STOPWORDS}


@lru_cache(maxsize=1)
def _index():
    """{slot: [token_set, ...]} built from the committed fingerprints."""
    try:
        with open(DATA_PATH, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {}

    index = {}
    for paper in payload.get("papers", []):
        for slot, item in (paper.get("items") or {}).items():
            bag = set(item.get("tokens") or ())
            if bag:
                index.setdefault(slot, []).append(bag)
    return index


def corpus_size():
    return sum(len(v) for v in _index().values())


# Below this, a comparison is meaningless rather than merely weak: "Se
# consideră numărul complex $z = 5+12i$" reduces to the single token
# {"complex"}, which scores a perfect 1.0 against any other complex-number
# statement. Treating that as a near-duplicate would be wrong.
MIN_TOKENS = 3


def overlap(text, slot):
    """Highest Jaccard overlap against official statements in the same slot.

    0.0 when the slot is unknown, or when either side has too few content
    tokens for the score to mean anything.
    """
    candidates = _index().get(slot)
    if not candidates:
        return 0.0

    bag = tokens_of(text)
    if len(bag) < MIN_TOKENS:
        return 0.0

    best = 0.0
    for other in candidates:
        if len(other) < MIN_TOKENS:
            continue
        union = bag | other
        score = len(bag & other) / len(union)
        if score > best:
            best = score
    return round(best, 3)


def score_exam(exercises):
    """Per-slot overlap for a whole generated exam, plus the worst case.

    Returned as metadata, never as a veto - see the module docstring.
    """
    per_slot = {}
    for exercise in exercises:
        slot = exercise.get("slot")
        if not slot:
            continue
        per_slot[slot] = overlap(exercise.get("text", ""), slot)

    return {
        "per_slot": per_slot,
        "max": max(per_slot.values()) if per_slot else 0.0,
        "corpus_items": corpus_size(),
    }
