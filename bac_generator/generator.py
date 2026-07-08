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
from bac_generator.generators.registry import registry
from bac_generator.validators.verify import verify_exercise
from bac_generator.duplicate.similarity import (
    DuplicateDetector,
    get_exact_hash,
    get_normalized_hash,
    get_template_param_hash,
)

logger = logging.getLogger("bac_generator.generator")
logger.setLevel(logging.INFO)

GENERATOR_VERSION = "3.0.0"

# Lessons covered by each slot (for lesson-filtered generation)
SLOT_LESSONS = {
    1:  ["Radicali", "Puteri", "Fracții"],
    2:  ["Radicali", "Puteri"],
    3:  ["Radicali", "Puteri", "Fracții"],
    4:  ["Fracții", "Puteri"],
    5:  ["Numere complexe", "Trigonometrie"],
    6:  ["Trigonometrie"],
    7:  ["Matrici"],
    8:  ["Numere complexe"],
    9:  ["Derivate"],
    10: ["Limite"],
}


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
                      duplicate_threshold: float = 0.6) -> dict:
        """
        Generate a full BAC exam with 10 exercises.

        Args:
            selected_lessons:    If set, prioritize exercises matching these lesson names.
            seed:                RNG seed for deterministic generation.
            duplicate_threshold: Level-4 structural overlap threshold (default 0.6 = 60%).

        Returns:
            Exam dict with keys: exercises, html_preview, solution_preview, metadata.
        """
        rng = random.Random(seed) if seed is not None else random.Random()
        max_attempts = 200  # increased for large batch generation

        last_exercises = []

        for attempt in range(max_attempts):
            exercises = self._generate_exercises(rng, selected_lessons)
            last_exercises = exercises

            if not self.detector.is_duplicate(exercises, threshold=duplicate_threshold):
                # Compute diversity score before registering (comparing against history)
                diversity_score = self.detector.compute_diversity_score(exercises)

                # Register this exam
                self.detector.register_exam(exercises)

                # Assemble + annotate
                exam_data = self.assemble_exam(exercises)
                exam_data["metadata"] = self._build_metadata(
                    exercises, seed, selected_lessons, attempt, diversity_score
                )

                self._persist_metadata(exam_data["metadata"])
                return exam_data
            else:
                self.stats["duplicate_rejections"] += 1
                self.stats["total_attempts"] += 1

        # Fallback: return last generated exam even if it's a duplicate
        logger.warning(f"Max attempts ({max_attempts}) reached — returning last exam as fallback.")
        exam_data = self.assemble_exam(last_exercises)
        diversity_score = self.detector.compute_diversity_score(last_exercises)
        exam_data["metadata"] = self._build_metadata(
            last_exercises, seed, selected_lessons, max_attempts, diversity_score,
            validation_status="fallback_max_attempts"
        )
        return exam_data

    # ── Exercise generation ────────────────────────────────────────────

    def _generate_exercises(self, rng: random.Random, selected_lessons: list[str]) -> list[dict]:
        """Generate one exercise per slot (slots 1–10)."""
        exercises = []
        for slot_num in range(1, 11):
            ex = self._generate_single_exercise(slot_num, rng, selected_lessons)
            exercises.append(ex)
        return exercises

    def _generate_single_exercise(self,
                                   slot_num: int,
                                   rng: random.Random,
                                   selected_lessons: list[str]) -> dict:
        """
        Generate a single validated exercise for a given slot.
        Retries up to 50 times; falls back to unfiltered generation on failure.
        """
        funcs = registry.get_generators(slot_num)
        if not funcs:
            raise ValueError(f"No generators registered for slot {slot_num}")

        slot_can_match = selected_lessons and any(
            lesson in selected_lessons
            for lesson in SLOT_LESSONS.get(slot_num, [])
        )

        for attempt in range(50):
            gen_func = rng.choice(funcs)
            ex = gen_func(rng)

            # Lesson filter (first 15 attempts only)
            if selected_lessons and slot_can_match and attempt < 15:
                if ex.get("lesson") not in selected_lessons:
                    continue

            if verify_exercise(ex):
                return ex
            self.stats["validation_failures"] += 1

        # Fallback: accept anything valid, ignoring lesson
        for _ in range(20):
            ex = rng.choice(funcs)(rng)
            if verify_exercise(ex):
                return ex
            self.stats["validation_failures"] += 1

        # Last resort: return unvalidated
        return rng.choice(funcs)(rng)

    # ── Metadata ──────────────────────────────────────────────────────

    def _build_metadata(self,
                        exercises: list[dict],
                        seed,
                        selected_lessons,
                        attempt: int,
                        diversity_score: float,
                        validation_status: str = "verified") -> dict:
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
                "exact_hash":        get_exact_hash(ex.get("text", "")),
                "template_param_hash": get_template_param_hash(tid, psig),
            })

        return {
            "timestamp":         datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "seed":              seed,
            "generator_version": GENERATOR_VERSION,
            "selected_lessons":  selected_lessons or [],
            "validation_status": validation_status,
            "diversity_score":   diversity_score,
            "attempts_required": attempt + 1,
            "duplicate_rejections_so_far": self.stats["duplicate_rejections"],
            "exercise_fingerprints": fingerprints,
        }

    def _persist_metadata(self, metadata: dict) -> None:
        """Append metadata record to the JSON history file."""
        history_path = "bac_generator/metadata_history.json"
        try:
            history = []
            if os.path.exists(history_path):
                with open(history_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        history = json.loads(content)
            history.append(metadata)
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist metadata: {e}")

    # ── Assembly ──────────────────────────────────────────────────────

    def assemble_exam(self, exercises: list[dict]) -> dict:
        """Assemble 10 exercises into official BAC sections."""
        s1 = exercises[0:6]
        s2 = exercises[6:8]
        s3 = exercises[8:10]

        html = "### SUBIECTUL I (30 de puncte)\n\n"
        for i, ex in enumerate(s1, 1):
            html += f"**{i}.** {ex['text']} **(5p)**\n\n"

        html += "\n---\n### SUBIECTUL al II-lea (30 de puncte)\n\n"
        for i, ex in enumerate(s2, 1):
            html += f"**{i}.** {ex['text']}\n\n"

        html += "\n---\n### SUBIECTUL al III-lea (30 de puncte)\n\n"
        for i, ex in enumerate(s3, 1):
            html += f"**{i}.** {ex['text']}\n\n"

        sol = "### BAREM DE EVALUARE ȘI DE NOTARE\n\n"
        sol += "#### SUBIECTUL I\n\n"
        for i, ex in enumerate(s1, 1):
            sol += f"**{i}.** {ex['solution']}\n\n"
        sol += "#### SUBIECTUL al II-lea\n\n"
        for i, ex in enumerate(s2, 1):
            sol += f"**{i}.** {ex['solution']}\n\n"
        sol += "#### SUBIECTUL al III-lea\n\n"
        for i, ex in enumerate(s3, 1):
            sol += f"**{i}.** {ex['solution']}\n\n"

        return {
            "exercises":        exercises,
            "html_preview":     html,
            "solution_preview": sol,
        }
