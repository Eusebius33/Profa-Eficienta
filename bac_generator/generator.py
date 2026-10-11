"""
BACExamGenerator — orchestrates production of a complete Romanian BAC Mathematics exam.

Architecture v3.0:
- Template-parameter separation via @template decorator in generators/base.py
- 5 variants per slot (50 total templates across 10 slots)
- 4-level duplicate detection (exact/template+params/template-only/structural)
- Per-exam diversity scoring
- Deterministic generation via seed
- Rich metadata persistence (template_ids, param_signatures, diversity_score)
"""
import random
import os
import json
import datetime
import logging
from bac_generator import coverage as coverage_mod
from bac_generator import structure
from bac_generator.generators import difficulty as difficulty_mod
from bac_generator.generators.registry import registry
from bac_generator.validators.verify import verify_exercise
from bac_generator.duplicate import corpus_overlap
from bac_generator.duplicate.similarity import (
    DuplicateDetector,
    get_exact_hash,
    get_normalized_hash,
    get_template_param_hash,
)

logger = logging.getLogger("bac_generator.generator")
logger.setLevel(logging.INFO)

GENERATOR_VERSION = "4.0.0"

# The slot->lesson map and the forced-omission rule are derived from the mined
# corpus now, not hand-written - the hand-written one had Numere complexe /
# Trigonometrie at Subiect I item 5, where 100% of real M_tehnologic papers
# carry Geometrie analitica. Re-exported here because bac_generator/routes.py
# and the mode5 lesson picker import them from this module.
SLOT_LESSONS = structure.SLOT_LESSONS


def forced_lessons(omitted_lessons, profile: str = structure.DEFAULT_PROFILE):
    """Lessons that show up however hard we try to omit them.

    The official structure fixes what each slot is about, so a slot whose every
    lesson has been omitted still has to produce one of them - handing back an
    exam that is a subject short would be worse.
    """
    return structure.forced_lessons(profile, omitted_lessons)


class BACExamGenerator:
    """
    Orchestrates generation of a complete 10-exercise BAC exam.

    Each exam:
      - Contains exercises for slots 1–10 (official BAC structure)
      - Is validated mathematically (SymPy + bounds checks)
      - Is checked for uniqueness across 4 duplication levels
      - Receives a diversity score relative to recent past exams
      - Has its metadata persisted for auditing

    To add a new exercise variant:
      1. Add a function decorated with @registry.register(slot=N) and @template(...)
      2. No other changes required — the registry picks it up automatically.
    """

    def __init__(self):
        self.detector = DuplicateDetector()
        self.stats = {
            "validation_failures": 0,
            "duplicate_rejections": 0,
            "total_attempts": 0,
        }

    def generate_exam(self,
                      selected_lessons: list[str] = None,
                      seed: int = None,
                      duplicate_threshold: float = 0.6,
                      accent: str = None,
                      omitted_lessons: list[str] = None,
                      *,
                      profile: str = None,
                      difficulty: str = None) -> dict:
        """
        Generate a full BAC exam with 10 exercises.

        Args:
            selected_lessons:    If set, prioritize exercises matching these lesson names.
            seed:                RNG seed for deterministic generation.
            duplicate_threshold: Level-4 structural overlap threshold (default 0.6 = 60%).
            accent:              A single lesson to push to the front of the queue: every
                                 slot that can serve it generates it in preference to the
                                 rest of `selected_lessons`.
            omitted_lessons:     Lessons to keep out of the exam entirely. They win over
                                 both `accent` and `selected_lessons`.
            profile:             M1 / M2 / M3 / M_PED. Decides the paper's shape and
                                 which lesson each slot draws from. Keyword-only, because
                                 existing callers pass `selected_lessons` positionally.
            difficulty:          usor / mediu / dificil / olimpic. `mediu` reproduces the
                                 previous output exactly.

        Returns:
            Exam dict with keys: exercises, units, structure, html_preview,
            solution_preview, profile, difficulty, metadata.
        """
        profile = structure.resolve_profile(profile)
        level = difficulty_mod.normalize_level(difficulty)
        omitted_lessons = list(omitted_lessons or [])
        if accent and accent in omitted_lessons:
            accent = None

        rng = random.Random(seed) if seed is not None else random.Random()
        max_attempts = 200  # increased for large batch generation

        last_exercises = []

        for attempt in range(max_attempts):
            exercises = self._generate_exercises(
                rng, selected_lessons, accent, omitted_lessons, profile, level
            )
            last_exercises = exercises

            if not self.detector.is_duplicate(exercises, threshold=duplicate_threshold):
                # Compute diversity score before registering (comparing against history)
                diversity_score = self.detector.compute_diversity_score(exercises)

                # Register this exam
                self.detector.register_exam(exercises)

                # Assemble + annotate
                exam_data = self.assemble_exam(exercises, profile=profile, difficulty=level)
                exam_data["metadata"] = self._build_metadata(
                    exercises, seed, selected_lessons, attempt, diversity_score,
                    accent=accent, omitted_lessons=omitted_lessons,
                    profile=profile, difficulty=level, exam_data=exam_data
                )

                self._persist_metadata(exam_data["metadata"])
                return exam_data
            else:
                self.stats["duplicate_rejections"] += 1
                self.stats["total_attempts"] += 1

        # Fallback: return last generated exam even if it's a duplicate
        logger.warning(f"Max attempts ({max_attempts}) reached — returning last exam as fallback.")
        exam_data = self.assemble_exam(last_exercises, profile=profile, difficulty=level)
        diversity_score = self.detector.compute_diversity_score(last_exercises)
        exam_data["metadata"] = self._build_metadata(
            last_exercises, seed, selected_lessons, max_attempts, diversity_score,
            validation_status="fallback_max_attempts",
            accent=accent, omitted_lessons=omitted_lessons,
            profile=profile, difficulty=level, exam_data=exam_data
        )
        return exam_data

    # ── Exercise generation ────────────────────────────────────────────

    def _generate_exercises(self,
                            rng: random.Random,
                            selected_lessons: list[str],
                            accent: str = None,
                            omitted_lessons: list[str] = None,
                            profile: str = None,
                            level: str = None) -> list[dict]:
        """One exercise per slot of this profile's paper.

        M1/M2/M3 have ten slots (six Subiect I items plus four problems); the
        pedagogic paper has eight (six items plus two single-theme subjects).
        """
        profile = structure.resolve_profile(profile)
        level = difficulty_mod.normalize_level(level)

        exercises = []
        for slot in structure.slots_for(profile):
            ex = self._generate_single_exercise(
                slot, rng, selected_lessons, accent, omitted_lessons, profile, level
            )
            ex["slot"] = slot
            exercises.append(ex)
        return exercises

    def _generate_single_exercise(self,
                                   slot: str,
                                   rng: random.Random,
                                   selected_lessons: list[str],
                                   accent: str = None,
                                   omitted_lessons: list[str] = None,
                                   profile: str = None,
                                   level: str = None) -> dict:
        """
        Generate a single validated exercise for one slot.

        Lesson preference, strongest first:
          1. `accent`, whenever this slot is one that can teach it;
          2. otherwise the slot's share of `selected_lessons`;
          3. otherwise whatever the corpus says belongs in this slot, drawn in
             proportion to how often it actually appears there.
        `omitted_lessons` is a veto at every stage - it is only given up on in
        the last-resort branch, where there is nothing valid left to return.

        Retries up to 50 times; falls back to unfiltered generation on failure.
        """
        profile = structure.resolve_profile(profile)
        level = difficulty_mod.normalize_level(level)

        funcs = registry.get_generators(structure.legacy_slot(slot))
        if not funcs:
            raise ValueError(f"No generators registered for slot {slot}")

        # Templates that declare themselves unsuitable for this level are
        # dropped, unless that would empty the slot - see difficulty.suitable.
        funcs = difficulty_mod.suitable(funcs, level)

        omitted = set(omitted_lessons or ())
        slot_lessons = structure.slot_lessons(profile, slot)
        weights = structure.slot_weights(profile, slot)

        slot_can_match = bool(selected_lessons) and any(
            lesson in selected_lessons for lesson in slot_lessons
        )

        if accent and accent in slot_lessons and accent not in omitted:
            preferred = {accent}
        elif slot_can_match:
            preferred = {l for l in selected_lessons if l not in omitted}
        else:
            # Nothing was asked for, so follow the corpus: a lesson that fills
            # this slot in 80% of real papers should fill it in 80% of ours.
            preferred = self._weighted_lesson(rng, weights, omitted)

        for attempt in range(50):
            gen_func = rng.choice(funcs)
            ex = gen_func(difficulty_mod.wrap(rng, level))
            lesson = ex.get("lesson")

            if lesson in omitted:
                continue

            if preferred and attempt < 15 and lesson not in preferred:
                continue

            if verify_exercise(ex):
                ex["difficulty_level"] = level
                return ex
            self.stats["validation_failures"] += 1

        for _ in range(20):
            ex = rng.choice(funcs)(difficulty_mod.wrap(rng, level))
            if ex.get("lesson") in omitted:
                continue
            if verify_exercise(ex):
                ex["difficulty_level"] = level
                return ex
            self.stats["validation_failures"] += 1

        ex = rng.choice(funcs)(difficulty_mod.wrap(rng, level))
        ex["difficulty_level"] = level
        return ex

    @staticmethod
    def _weighted_lesson(rng, weights, omitted):
        """Pick one lesson for a slot in proportion to its corpus share.

        Returns a single-element set so it slots into the same preference check
        as `accent`. Empty when the blueprint knows nothing about this slot, in
        which case the caller leaves the slot unfiltered.
        """
        pool = [(lesson, share) for lesson, share in weights.items() if lesson not in omitted]
        if not pool:
            return set()

        # Shares are fractions of all real papers and need not sum to 1 - a
        # slot where the corpus only recognised Logaritmi 19% of the time is
        # 81% something else. Drawing against 1.0 rather than against the sum
        # preserves that: the leftover falls through to an unfiltered draw
        # instead of handing the whole slot to the one topic we could name.
        cutoff = rng.random()
        running = 0.0
        for lesson, share in pool:
            running += share
            if cutoff <= running:
                return {lesson}
        return set()

    # ── Metadata ──────────────────────────────────────────────────────

    def _build_metadata(self,
                        exercises: list[dict],
                        seed,
                        selected_lessons,
                        attempt: int,
                        diversity_score: float,
                        validation_status: str = "verified",
                        accent: str = None,
                        omitted_lessons: list[str] = None,
                        profile: str = None,
                        difficulty: str = None,
                        exam_data: dict = None) -> dict:
        """Build rich per-exam metadata dict."""
        fingerprints = []
        for ex in exercises:
            tid  = ex.get("template_id", ex.get("id", ""))
            psig = ex.get("param_signature", "")
            fingerprints.append({
                "id":                ex.get("id", ""),
                "template_id":       tid,
                "param_signature":   psig,
                "topic":             ex.get("topic", ex.get("lesson", "")),
                "difficulty":        ex.get("difficulty", "medium"),
                "slot":              ex.get("slot"),
                "lesson":            ex.get("lesson", ""),
                "exact_hash":        get_exact_hash(ex.get("text", "")),
                "template_param_hash": get_template_param_hash(tid, psig),
            })

        exam_lessons = {ex.get("lesson") for ex in exercises}

        exam_data = exam_data or {}

        return {
            "timestamp":         datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "seed":              seed,
            "generator_version": GENERATOR_VERSION,
            "profile":           structure.resolve_profile(profile),
            "difficulty":        difficulty_mod.normalize_level(difficulty),
            "points_awarded":    exam_data.get("points_awarded"),
            "points_expected":   exam_data.get("points_expected"),
            "assembly_issues":   exam_data.get("assembly_issues", []),
            # What this profile/level can really deliver, so the UI never has
            # to guess whether a short paper was intentional.
            "coverage":          coverage_mod.coverage_report(profile, difficulty),
            # How close each statement came to an official one. Reported, not
            # enforced - see duplicate/corpus_overlap.py for why.
            "corpus_overlap":    corpus_overlap.score_exam(exercises),
            "selected_lessons":  selected_lessons or [],
            "accent":            accent,
            "omitted_lessons":   omitted_lessons or [],
            # Omissions the fixed slot structure would not let us honour.
            "omitted_not_honoured": sorted(exam_lessons & set(omitted_lessons or ())),
            "validation_status": validation_status,
            "diversity_score":   diversity_score,
            "attempts_required": attempt + 1,
            "duplicate_rejections_so_far": self.stats["duplicate_rejections"],
            "exercise_fingerprints": fingerprints,
        }

    # One JSON object per line, appended. The previous version read the whole
    # file, appended in memory and rewrote it - with gunicorn running three
    # workers that races and truncates. It also used a CWD-relative path, so it
    # silently wrote nothing unless the process happened to start in the repo
    # root. Both matter more now that the history is worth reading back.
    HISTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "metadata_history.jsonl")

    def _persist_metadata(self, metadata: dict) -> None:
        """Append one metadata record to the history log."""
        try:
            with open(self.HISTORY_PATH, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist metadata: {e}")

    # ── Assembly ──────────────────────────────────────────────────────

    def assemble_exam(self, exercises: list[dict], profile: str = None,
                      difficulty: str = None) -> dict:
        """Lay the generated exercises out as the profile's real paper.

        A real BAC paper is eighteen separately-marked pieces worth 5p each
        (90p, plus 10p din oficiu). Subiect I contributes six items; each
        Subiect II/III problem contributes its a)/b)/c) subpoints. `units` is
        that flat marked-up view - the thing a teacher grades against - while
        `exercises` keeps its original per-slot shape so stored exams and the
        duplicate detector carry on working.
        """
        profile = structure.resolve_profile(profile)
        level = difficulty_mod.normalize_level(difficulty)
        spec = structure.profile_spec(profile)
        by_slot = {ex.get("slot"): ex for ex in exercises}

        html_parts, sol_parts, units, issues = [], [], [], []
        sol_parts.append("### BAREM DE EVALUARE ȘI DE NOTARE\n")

        if level in difficulty_mod.ABOVE_BAC:
            html_parts.append(f"> **{difficulty_mod.ABOVE_BAC_NOTE}**\n")

        for subject in spec["subjects"]:
            name = structure.SUBJECT_NAMES[subject["subject"]]
            points = sum(
                structure.POINTS_PER_ITEM * (len(subject.get("subpoints") or [1]))
                if subject["kind"] == "problems" else structure.POINTS_PER_ITEM
                for _ in range(subject["count"])
            )
            html_parts.append(f"### {name} ({points} de puncte)\n")
            sol_parts.append(f"#### {name}\n")

            for position, slot in enumerate(subject["slots"], 1):
                ex = by_slot.get(slot)
                if ex is None:
                    continue

                slot_units, issue = structure.build_units(ex, subject)
                if issue:
                    issues.append({"slot": slot, "issue": issue})

                if subject["kind"] == "items":
                    unit = slot_units[0]
                    html_parts.append(f"**{position}.** {unit['text']} **({unit['points']}p)**\n")
                    sol_parts.append(f"**{position}.** {unit['solution']}\n")
                else:
                    stem, _ = structure.split_subpoints(ex.get("text", ""))
                    label = f"**{position}.**" if subject["kind"] == "problems" else ""
                    if stem:
                        html_parts.append(f"{label} {stem}".strip() + "\n")
                        sol_parts.append(f"{label} ".strip() + "\n")
                    for unit in slot_units:
                        tag = f"{unit['label']})" if unit["label"] else f"{position}."
                        html_parts.append(f"**{tag}** {unit['text']} **({unit['points']}p)**\n")
                        sol_parts.append(f"**{tag}** {unit['solution']}\n")

                for order, unit in enumerate(slot_units, 1):
                    units.append({
                        "subject": subject["subject"],
                        "slot": slot,
                        "position": position,
                        "label": unit["label"],
                        "order": order,
                        "points": unit["points"],
                        "lesson": ex.get("lesson"),
                        "text": unit["text"],
                        "solution": unit["solution"],
                    })

            html_parts.append("\n---\n")

        awarded = sum(u["points"] for u in units)

        return {
            "exercises":        exercises,
            "units":            units,
            "profile":          profile,
            "profile_label":    spec["label"],
            "difficulty":       level,
            "above_bac":        level in difficulty_mod.ABOVE_BAC,
            "structure":        spec["subjects"],
            "points_awarded":   awarded,
            "points_expected":  structure.total_points(profile),
            "points_bonus":     structure.OFFICIAL_BONUS,
            "assembly_issues":  issues,
            "html_preview":     "\n".join(html_parts).strip(),
            "solution_preview": "\n".join(sol_parts).strip(),
        }
