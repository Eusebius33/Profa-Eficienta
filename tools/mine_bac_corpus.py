#!/usr/bin/env python3
"""
Mine the official BAC corpus in BACVARIANTS/ into the small JSON artifacts the
generator reads at runtime.

    python3 tools/mine_bac_corpus.py            # write artifacts
    python3 tools/mine_bac_corpus.py --report   # print the distribution table
    python3 tools/mine_bac_corpus.py --check    # re-mine and diff, write nothing

OFFLINE ONLY. This shells out to `pdftotext` (poppler-utils), which is NOT a
Python package and is NOT in the Docker image. That is deliberate: the app must
never parse a PDF at request time. Re-run this by hand when new papers land in
BACVARIANTS/, and commit the artifacts it writes to bac_generator/data/.

WHY THE EXTRACTED STATEMENTS ARE NEVER REUSED
---------------------------------------------
The radical sign is absent from these PDFs' text layer entirely - it is drawn
as vector graphics, so no extractor recovers it (verified with PyPDF2,
`pdftotext -layout`, `pdftotext -raw` and `mutool stext`: zero U+221A glyphs).
Most integral signs go the same way, and sub/superscripts flatten, so x_1^3
comes out as "x13". An extracted statement therefore reads

    "Aratati ca 7 ( 7 + 1) - 7 = 7 ."

when the real exercise is

    "Aratati ca V7(V7+1) - 7 = 7 ."

which is simply false. Extracted text is used here for topic classification
(keywords are words, not glyphs) and for duplicate fingerprints, and for
nothing else. Teachers see generated exercises or the original PDFs, never
this text. The blueprint records an `unclassified` count per slot so the blind
spot is visible rather than silently rounding Radicali down to zero.

OUTPUTS (bac_generator/data/)
-----------------------------
blueprint.json              measured topic distribution per profile per slot
official_fingerprints.json  per-paper topic sequences + per-item token bags
archive_index.json          profile/year/session/variant + relative PDF path
"""

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, "BACVARIANTS", "BAC_PREV_SUBJECTS")
OUT_DIR = os.path.join(ROOT, "bac_generator", "data")

PROFILE_DIRS = {"m1": "M1", "m2": "M2", "m3 teh": "M3", "m3 peda": "M_PED"}

# Ordered, first match wins. Order is load-bearing: a derivative problem says
# "funcția f" in its stem, so a bare Funcții rule placed first would swallow
# every analysis problem in the corpus. Structural markers precede lexical ones.
TOPIC_RULES = [
    ("Integrale definite",  [r"\bintegral", r"primitiv", r"aria suprafe", r"volumul corpului"]),
    ("Derivate",            [r"derivat", r"f\s*'", r"asimptot", r"punct de extrem", r"monoton", r"convex"]),
    ("Limite",              [r"\blim\b"]),
    ("Matrici",             [r"matric", r"\bdet\s*\(", r"determinant", r"\bI_?2\b"]),
    ("Legi de compoziție",  [r"lege de compozi", r"element neutru", r"\bgrup\b", r"asociativ", r"comutativ", r"simetricul"]),
    ("Polinoame",           [r"polinom"]),
    ("Geometrie analitică", [r"reperul cartezian", r"\bxOy\b", r"vector", r"coliniar", r"panta dreptei"]),
    ("Procente",            [r"procent", r"ieftinir", r"scumpir", r"reducere cu", r"\d\s*%"]),
    ("Probabilități",       [r"probabilitat", r"cifre distincte", r"submul[țt]im"]),
    ("Numere complexe",     [r"complex", r"conjugat"]),
    ("Logaritmi",           [r"logaritm", r"\blog\b", r"\bln\b"]),
    ("Trigonometrie",       [r"\bsin\b", r"\bcos\b", r"\btg\b", r"\bctg\b"]),
    ("Geometrie plană",     [r"triunghi", r"\barie", r"median", r"\bcerc", r"paralelogram", r"ipotenuz"]),
    ("Progresii",           [r"progresi"]),
    ("Funcții",             [r"func[țt]i", r"graficul"]),
    ("Ecuații",             [r"ecua[țt]i", r"inecua"]),
]
COMPILED = [(name, [re.compile(p, re.I) for p in pats]) for name, pats in TOPIC_RULES]

# M_pedagogic contains no analysis whatsoever. Without this, stray "dx"-ish
# matches score a phantom Integrale share on pedagogic matrix subjects.
PROFILE_FORBIDDEN = {"M_PED": {"Derivate", "Integrale definite", "Limite"}}

# Subiect I item 1 is the radicali/puteri slot and item 3 is often an irrational
# equation. Both are exactly where the missing radical glyph destroys detection,
# so their shares are hand-authored from reading the papers rather than measured.
SLOT_OVERRIDES = {
    "M1":    {"I.1": {"Numere complexe": 0.30, "Progresii": 0.25, "Radicali": 0.25, "Puteri": 0.20}},
    "M2":    {"I.1": {"Progresii": 0.39, "Radicali": 0.31, "Puteri": 0.30}},
    "M3":    {"I.1": {"Radicali": 0.40, "Puteri": 0.35, "Progresii": 0.25}},
    "M_PED": {"I.1": {"Radicali": 0.40, "Puteri": 0.36, "Progresii": 0.24}},
}

SUBJECT_RE = re.compile(r"SUBIECTUL\s+(?:al\s+)?(I{1,3})(?:-lea)?\b", re.I)
ITEM_RE = re.compile(r"\n?\s*5p\s+(?:[1-6]|[a-d])\s*[.)]\s*")
PROBLEM_RE = re.compile(r"\n\s{0,12}([12])\.\s")
BAREM_RE = re.compile(r"BAREM\s+DE\s+EVALUARE", re.I)
YEAR_RE = re.compile(r"(20[0-9]{2})")
VARIANT_RE = re.compile(r"(?:Subiect|var)_?(\d{1,2})", re.I)

STOPWORDS = {
    "care", "sunt", "este", "pentru", "orice", "unde", "intr", "intre", "din", "dintre",
    "cu", "si", "sau", "in", "la", "de", "a", "al", "ale", "un", "o", "se", "ca", "ce",
    "numarul", "numerele", "numar", "real", "reale", "naturale", "multimea", "consider",
    "considera", "aratati", "determinati", "calculati", "demonstrati", "rezolvati",
}
MIN_ITEMS = 5
KEEP_ABOVE = 0.12
MAX_TOKENS = 12


def pdf_text(path):
    """`pdftotext -layout` keeps Romanian diacritics and lays matrices out in
    2-D; PyPDF2 mangles both badly enough to break classification."""
    try:
        return subprocess.run(
            ["pdftotext", "-layout", path, "-"],
            capture_output=True, text=True, timeout=60,
        ).stdout or ""
    except subprocess.TimeoutExpired:
        return ""


def classify(text, profile):
    """Primary topic for one slot, or None. First matching rule wins."""
    forbidden = PROFILE_FORBIDDEN.get(profile, frozenset())
    for name, patterns in COMPILED:
        if name in forbidden:
            continue
        if any(p.search(text) for p in patterns):
            return name
    return None


def fold(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def skeleton(text):
    """Hash the SHAPE of a statement: numbers blanked, diacritics folded."""
    flat = re.sub(r"\s+", " ", fold(text)).strip()
    flat = re.sub(r"\d+", "#", flat)
    return hashlib.sha256(flat.encode("utf-8")).hexdigest()[:16]


def tokens_of(text):
    """The distinctive content words. Token overlap survives the glyph loss that
    makes exact hashing useless against this corpus, so this is what the
    similarity check can actually use."""
    words = re.findall(r"[a-z]{4,}", fold(text))
    counts = collections.Counter(w for w in words if w not in STOPWORDS)
    return [w for w, _ in counts.most_common(MAX_TOKENS)]


def parse_paper(text, profile):
    """Split one paper into {slot_key: text}.

    Subiect I is keyed by item position (I.1 .. I.6). Subiects II and III are
    keyed per PROBLEM (II.p1, II.p2) and carry the stem plus all its subpoints,
    because the topic lives in the stem - "Se consideră matricele A = ..." -
    not in the a)/b)/c) lines under it.

    M_pedagogic is a different paper: all three subjects are six numbered items,
    and II/III explore a single theme, so each is keyed as one `tema` block.
    """
    slots = {}
    parts = SUBJECT_RE.split(text)
    for i in range(1, len(parts) - 1, 2):
        roman, body = parts[i].upper(), parts[i + 1]

        if roman == "I":
            items = [re.sub(r"\s+", " ", c).strip() for c in ITEM_RE.split(body)[1:]]
            if len(items) < MIN_ITEMS:
                continue
            for pos, item in enumerate(items[:6], 1):
                slots[f"I.{pos}"] = item
            continue

        if profile == "M_PED":
            slots[f"{roman}.tema"] = re.sub(r"\s+", " ", body).strip()
            continue

        segments = PROBLEM_RE.split(body)
        for j in range(1, len(segments) - 1, 2):
            slots[f"{roman}.p{segments[j]}"] = re.sub(r"\s+", " ", segments[j + 1]).strip()

    return slots


def paper_meta(filename, profile):
    year = YEAR_RE.search(filename)
    variant = VARIANT_RE.search(filename)
    low = filename.lower()
    if "model" in low:
        session = "model"
    elif "simulare" in low:
        session = "simulare"
    elif "_s1_" in low:
        session = "sesiunea 1"
    elif "_s2_" in low:
        session = "sesiunea 2"
    elif "_ss_" in low:
        session = "sesiune specială"
    else:
        session = "sesiunea principală"
    return {
        "profile": profile,
        "year": int(year.group(1)) if year else None,
        "session": session,
        "variant": variant.group(1) if variant else None,
    }


def mine():
    counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    unclassified = collections.defaultdict(collections.Counter)
    seen = collections.defaultdict(collections.Counter)
    fingerprints, archive, skipped = [], [], []

    for folder, profile in sorted(PROFILE_DIRS.items()):
        folder_path = os.path.join(CORPUS_DIR, folder)
        if not os.path.isdir(folder_path):
            skipped.append((folder, "missing folder"))
            continue

        for filename in sorted(os.listdir(folder_path)):
            if not filename.lower().endswith(".pdf"):
                continue
            # "... (1).pdf" are byte-identical re-downloads; counting them twice
            # would over-weight those years in the blueprint.
            if "(1)" in filename:
                skipped.append((filename, "duplicate scan"))
                continue

            path = os.path.join(folder_path, filename)
            text = pdf_text(path)
            if not text.strip():
                skipped.append((filename, "no extractable text"))
                continue

            # Exactly one file in the corpus is a marking scheme wearing a
            # "Subiect" filename. Its answers would poison every topic share.
            if BAREM_RE.search(text[:3000]):
                skipped.append((filename, "barem, not a subject paper"))
                continue

            slots = parse_paper(text, profile)
            if not slots:
                skipped.append((filename, "unparseable"))
                continue

            meta = paper_meta(filename, profile)
            archive.append({
                **meta,
                "id": f"{profile}-{meta['year']}-{meta['session'].replace(' ', '_')}-{meta['variant'] or 'x'}",
                "path": os.path.relpath(path, ROOT),
                "filename": filename,
                "bytes": os.path.getsize(path),
            })

            topics_here, items_here = {}, {}
            for slot_key, slot_text in slots.items():
                seen[profile][slot_key] += 1
                topic = classify(slot_text, profile)
                if topic:
                    counts[profile][slot_key][topic] += 1
                    topics_here[slot_key] = topic
                else:
                    unclassified[profile][slot_key] += 1
                items_here[slot_key] = {
                    "skeleton": skeleton(slot_text),
                    "tokens": tokens_of(slot_text),
                }

            fingerprints.append({**meta, "topics": topics_here, "items": items_here})

    return counts, unclassified, seen, fingerprints, archive, skipped


def build_blueprint(counts, unclassified, seen, fingerprints):
    blueprint = {
        "schema": 1,
        "generated": date.today().isoformat(),
        "source": "BACVARIANTS/BAC_PREV_SUBJECTS",
        "papers": len(fingerprints),
        "note": (
            "Topic shares measured from official papers. I.1 is hand-authored because the "
            "radical glyph is absent from the PDF text layer; `unclassified` records how "
            "many papers a slot could not be read from."
        ),
        "profiles": {},
    }

    for profile in PROFILE_DIRS.values():
        slot_map = {}
        for slot_key in counts[profile]:
            n = max(seen[profile][slot_key], 1)
            dist = {
                topic: round(hits / n, 3)
                for topic, hits in counts[profile][slot_key].most_common()
                if hits / n >= KEEP_ABOVE
            }
            if dist:
                slot_map[slot_key] = {
                    "n": n,
                    "unclassified": unclassified[profile].get(slot_key, 0),
                    "topics": dist,
                }

        for slot_key, dist in SLOT_OVERRIDES.get(profile, {}).items():
            slot_map[slot_key] = {
                "n": seen[profile].get(slot_key, 0),
                "unclassified": unclassified[profile].get(slot_key, 0),
                "topics": dist,
                "hand_authored": True,
            }

        blueprint["profiles"][profile] = {
            "papers": sum(1 for f in fingerprints if f["profile"] == profile),
            "slots": dict(sorted(slot_map.items(), key=lambda kv: (len(kv[0].split(".")[0]), kv[0]))),
        }

    return blueprint


def write(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")


def report(blueprint):
    for profile, data in blueprint["profiles"].items():
        print(f"\n### {profile}  ({data['papers']} papers)")
        for slot, info in data["slots"].items():
            tag = " [hand]" if info.get("hand_authored") else ""
            unk = f"  ?{info['unclassified']}" if info.get("unclassified") else ""
            share = ", ".join(f"{t} {int(s*100)}%" for t, s in list(info["topics"].items())[:4])
            print(f"  {slot:8} {share}{tag}{unk}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="print the distribution table")
    parser.add_argument("--check", action="store_true", help="re-mine and diff; write nothing")
    args = parser.parse_args()

    if not shutil.which("pdftotext"):
        sys.exit("pdftotext not found. Install poppler-utils:  sudo apt install poppler-utils")
    if not os.path.isdir(CORPUS_DIR):
        sys.exit(f"corpus not found at {CORPUS_DIR}")

    counts, unclassified, seen, fingerprints, archive, skipped = mine()
    blueprint = build_blueprint(counts, unclassified, seen, fingerprints)

    print(f"papers mined: {len(fingerprints)}")
    for profile in PROFILE_DIRS.values():
        data = blueprint["profiles"][profile]
        print(f"  {profile:6} {data['papers']:3} papers, {len(data['slots'])} slots")
    if skipped:
        print(f"skipped {len(skipped)}:")
        for name, why in skipped:
            print(f"  {why:28} {name}")

    if args.report:
        report(blueprint)

    if args.check:
        existing = os.path.join(OUT_DIR, "blueprint.json")
        if not os.path.exists(existing):
            sys.exit("--check: no committed blueprint.json to compare against")
        with open(existing, encoding="utf-8") as handle:
            old = json.load(handle)
        same = old.get("profiles") == blueprint["profiles"]
        print("\n--check:", "artifacts are up to date" if same else "ARTIFACTS ARE STALE")
        sys.exit(0 if same else 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    write(os.path.join(OUT_DIR, "blueprint.json"), blueprint)
    write(os.path.join(OUT_DIR, "official_fingerprints.json"),
          {"schema": 1, "generated": date.today().isoformat(), "papers": fingerprints})
    write(os.path.join(OUT_DIR, "archive_index.json"),
          {"schema": 1, "generated": date.today().isoformat(),
           "papers": sorted(archive, key=lambda p: (p["profile"], -(p["year"] or 0), p["filename"])),
           "skipped": [{"filename": n, "reason": w} for n, w in skipped]})

    for name in ("blueprint.json", "official_fingerprints.json", "archive_index.json"):
        size = os.path.getsize(os.path.join(OUT_DIR, name))
        print(f"  wrote bac_generator/data/{name}  ({size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
