"""
What a profile/difficulty combination can actually deliver, said plainly.

The generator will always hand back a paper. That is the right behaviour - a
subject short is worse than a substituted exercise - but it means a teacher
can print something that quietly differs from what they asked for. This module
is what stops that being a surprise:

  native   the slot has templates for the lesson the corpus puts there, at the
           requested difficulty
  reused   templates exist, but not for this shape or this level; the slot was
           filled with the closest thing available
  missing  nothing can fill this slot

Today the honest answers are that M_pedagogic's Subiects II and III are
`reused` (its single-theme six-item shape has no template family, so those
subjects come out at 15p instead of 30p), and that `olimpic` is `reused`
almost everywhere because no template declares itself olympiad-level.
"""

from bac_generator import structure
from bac_generator.generators import difficulty as difficulty_mod
from bac_generator.generators.registry import registry

NATIVE = "native"
REUSED = "reused"
MISSING = "missing"


def _lessons_available(slot):
    """Lessons the templates registered for this slot can actually emit."""
    import random

    rng = random.Random(0)
    lessons = set()
    for func in registry.get_generators(structure.legacy_slot(slot)):
        for _ in range(6):
            try:
                lessons.add(func(rng).get("lesson"))
            except Exception:
                break
    return lessons


def slot_report(profile, slot, level):
    profile = structure.resolve_profile(profile)
    level = difficulty_mod.normalize_level(level)
    subject = structure.subject_of(profile, slot)
    funcs = registry.get_generators(structure.legacy_slot(slot))

    if not funcs:
        return {"slot": slot, "status": MISSING,
                "reason": "Nu există niciun exercițiu înregistrat pentru acest slot."}

    wanted = set(structure.slot_lessons(profile, slot))
    available = _lessons_available(slot)
    at_level = difficulty_mod.suitable(funcs, level)
    level_native = any(level in difficulty_mod.template_bands(f) for f in funcs)

    reasons = []
    status = NATIVE

    # The pedagogic paper explores one theme over six numbered items; every
    # template we have for those slots emits an a)/b)/c) triple instead.
    if subject and subject["kind"] == "tema" and slot not in structure.NATIVE_TEMA_SLOTS:
        status = REUSED
        reasons.append(
            "Formatul pedagogic (o temă, 6 itemi) nu are încă exerciții proprii; "
            "slotul este completat cu un exercițiu în 3 subpuncte, deci subiectul "
            "valorează 15p în loc de 30p."
        )

    uncovered = sorted(l for l in wanted if l and l not in available)
    if uncovered:
        status = REUSED if status == NATIVE else status
        reasons.append(
            "Lecții pe care corpusul le pune aici, dar pentru care nu avem exerciții: "
            + ", ".join(uncovered) + "."
        )

    if not level_native:
        status = REUSED if status == NATIVE else status
        reasons.append(
            f"Niciun exercițiu nu este marcat pentru nivelul „{difficulty_mod.LEVEL_LABELS[level]}”; "
            f"s-au folosit cele existente, cu parametri ajustați."
        )

    return {
        "slot": slot,
        "status": status,
        "templates": len(funcs),
        "templates_at_level": len(at_level),
        "wanted_lessons": sorted(l for l in wanted if l),
        "uncovered_lessons": uncovered,
        "reason": " ".join(reasons),
    }


def coverage_report(profile, difficulty=None):
    """Per-slot status for one profile/difficulty, plus a one-line summary."""
    profile = structure.resolve_profile(profile)
    level = difficulty_mod.normalize_level(difficulty)

    slots = [slot_report(profile, slot, level) for slot in structure.slots_for(profile)]
    reused = [s for s in slots if s["status"] == REUSED]
    missing = [s for s in slots if s["status"] == MISSING]

    expected = structure.total_points(profile)
    # A reused tema slot delivers 15p where the real paper has 30p.
    shortfall = sum(
        15 for s in slots
        if s["status"] == REUSED
        and (structure.subject_of(profile, s["slot"]) or {}).get("kind") == "tema"
    )

    if missing:
        summary = f"{len(missing)} slot(uri) nu pot fi completate."
    elif shortfall:
        summary = (f"Variantă incompletă: {expected - shortfall} din {expected} puncte. "
                   f"{len(reused)} slot(uri) folosesc exerciții de alt format.")
    elif reused:
        summary = f"{len(reused)} slot(uri) folosesc exerciții apropiate, nu native."
    else:
        summary = "Toate sloturile sunt acoperite nativ."

    return {
        "profile": profile,
        "profile_label": structure.profile_spec(profile)["label"],
        "difficulty": level,
        "complete": not missing and not shortfall,
        "points_expected": expected,
        "points_deliverable": expected - shortfall,
        "above_bac": level in difficulty_mod.ABOVE_BAC,
        "summary": summary,
        "slots": slots,
    }
