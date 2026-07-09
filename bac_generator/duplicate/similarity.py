"""
Four-level duplicate detection system for the BAC Generator.

Levels:
  1. Exact text hash     — catches verbatim copies
  2. Template + params   — catches same template AND same parameter values
  3. Template only       — catches same mathematical structure with different numbers
  4. Structural overlap  — catches exams with too many shared template IDs (≥ threshold)

Diversity Score:
  Per-exam score in [0, 1] computed as:
      1 - avg_jaccard(current_template_ids, last N past exams)
  A score of 1.0 means no overlap with recent exams; 0.0 means identical to all recent exams.
"""

import re
import hashlib
import logging
import statistics
from typing import Optional

logger = logging.getLogger("bac_generator.duplicate")
logger.setLevel(logging.INFO)


# ──────────────────────────────────────────────────────────────────────
# Hash helpers
# ──────────────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Replace all numbers with [NUM] for template fingerprinting."""
    text = re.sub(r'-?\d+(?:\.\d+)?', '[NUM]', text)
    return re.sub(r'\s+', ' ', text).strip().lower()

def get_exact_hash(text: str) -> str:
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return hashlib.sha256(cleaned.encode('utf-8')).hexdigest()

def get_normalized_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode('utf-8')).hexdigest()

def get_template_param_hash(template_id: str, param_signature: str) -> str:
    """Hash of (template_id, param_signature) — identifies same structure AND same params."""
    key = f"{template_id}||{param_signature}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


# ──────────────────────────────────────────────────────────────────────
# Diversity scoring helper
# ──────────────────────────────────────────────────────────────────────

def _jaccard(set_a: set, set_b: set) -> float:
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


# ──────────────────────────────────────────────────────────────────────
# DuplicateDetector
# ──────────────────────────────────────────────────────────────────────

class DuplicateDetector:
    """
    Four-level duplicate detection with diversity scoring.

    Registry contents per past exam:
        {
            "exact_hashes":        list[str]  — per-exercise exact hash
            "normalized_hashes":   list[str]  — per-exercise text-template hash (pos-aware)
            "template_param_hashes": list[str] — per-exercise (template_id, params) hash
            "template_ids":        list[str]  — per-exercise template_id
            "ids":                 list[str]  — per-exercise generator id (legacy)
        }
    """

    def __init__(self):
        self.exact_hashes: set[str] = set()
        self.template_param_hashes: set[str] = set()
        self.past_exams: list[dict] = []

        try:
            from bac_generator.duplicate.official_exams import OFFICIAL_EXAMS
            for exam in OFFICIAL_EXAMS:
                self.register_exam(exam)
        except ImportError:
            logger.warning("Could not load official_exams.py; starting empty.")

    # ── Registration ──────────────────────────────────────────────────

    def register_exam(self, exercises: list[dict]) -> None:
        exact, norm_h, tp_h, tids, ids = [], [], [], [], []
        for ex in exercises:
            text = ex.get("text", "")
            tid  = ex.get("template_id", ex.get("id", ""))
            psig = ex.get("param_signature", "")
            eid  = ex.get("id", "")

            eh  = get_exact_hash(text)
            nh  = get_normalized_hash(text)
            tph = get_template_param_hash(tid, psig)

            exact.append(eh)
            norm_h.append(nh)
            tp_h.append(tph)
            tids.append(tid)
            ids.append(eid)

            self.exact_hashes.add(eh)
            self.template_param_hashes.add(tph)

        self.past_exams.append({
            "exact_hashes":          exact,
            "normalized_hashes":     norm_h,
            "template_param_hashes": tp_h,
            "template_ids":          tids,
            "ids":                   ids,
        })
        logger.debug(f"Registered exam #{len(self.past_exams)} ({len(exercises)} exercises)")

    # ── Level checks ──────────────────────────────────────────────────

    def check_level_1(self, exercises: list[dict]) -> bool:
        """Level 1: Exact text match with any past exercise."""
        for ex in exercises:
            if get_exact_hash(ex.get("text", "")) in self.exact_hashes:
                logger.info(f"L1 hit: exact match on '{ex.get('id')}'")
                return True
        return False

    def check_level_2(self, exercises: list[dict]) -> bool:
        """Level 2: Same (template_id, param_signature) — same structure AND same numbers."""
        for ex in exercises:
            tid  = ex.get("template_id", ex.get("id", ""))
            psig = ex.get("param_signature", "")
            tph  = get_template_param_hash(tid, psig)
            if tph in self.template_param_hashes:
                logger.info(f"L2 hit: same template+params on template '{tid}'")
                return True
        return False

    def check_level_3(self, exercises: list[dict]) -> bool:
        """
        Level 3: Same (template_id, param_signature) at the same slot position in
        any past exam.  This catches structurally identical exercises with identical
        parameters placed at the same curriculum position — a stricter guard than
        Level 2 (which checks across all positions without position awareness).
        """
        current = [(ex.get("template_id", ex.get("id", "")),
                    ex.get("param_signature", "")) for ex in exercises]
        for past in self.past_exams:
            past_tids  = past.get("template_ids", past.get("ids", []))
            past_tphs  = past.get("template_param_hashes", [None]*len(past_tids))
            for pos in range(min(len(current), len(past_tids))):
                c_tid, c_psig = current[pos]
                p_tid = past_tids[pos]
                # Match: same template AND same params at same position
                if c_tid and c_tid == p_tid:
                    # Compute the expected tp_hash for past exam at this position
                    p_tph = past_tphs[pos] if pos < len(past_tphs) else None
                    c_tph = get_template_param_hash(c_tid, c_psig)
                    if p_tph and c_tph == p_tph:
                        logger.info(f"L3 hit: same template+params '{c_tid}' at position {pos}")
                        return True
        return False


    def check_level_4(self, exercises: list[dict], threshold: float = 0.9, window: int = 50) -> bool:
        """
        Level 4: Ordered structural fingerprint comparison.

        Computes the fraction of positions where both exams use the same template_id.
        Rejects if this fraction ≥ threshold in any of the last `window` past exams.

        A threshold of 0.9 means: reject only if 9 or more of 10 positions use the
        same template structure — i.e., the exam is nearly a structural clone.

        This is intentionally stricter than set-Jaccard to avoid false positives
        when the template pool is small (e.g., 50 templates across 10 slots means
        any two exams will share many templates just by slot constraints).

        Args:
            exercises:  Candidate exam exercise list.
            threshold:  Fraction of matching positions to reject (default 0.9 = 90%).
            window:     Number of most recent past exams to compare against (default 50).
        """
        current_tids = [ex.get("template_id", ex.get("id", "")) for ex in exercises]
        n = len(current_tids)
        recent = self.past_exams[-window:] if window > 0 else self.past_exams
        for past in recent:
            past_tids = past.get("template_ids", past.get("ids", []))
            m = min(n, len(past_tids))
            if m == 0:
                continue
            matches = sum(1 for i in range(m) if current_tids[i] and current_tids[i] == past_tids[i])
            frac = matches / m
            if frac >= threshold:
                logger.info(f"L4 hit: {matches}/{m} matching template positions ({frac*100:.0f}% >= {threshold*100:.0f}%)")
                return True
        return False



    # ── Legacy shim for old Level 3 calls ─────────────────────────────
    def check_level_3_legacy(self, exercises: list[dict], threshold: float = 0.6) -> bool:
        """Backward-compatible alias for old Level 3 (structural overlap)."""
        return self.check_level_4(exercises, threshold)

    # ── Combined check ─────────────────────────────────────────────────

    def is_duplicate(self, exercises: list[dict], threshold: float = 0.6, window: int = 50) -> bool:
        """
        Runs all four levels in order. Returns True on the first match.

        Args:
            exercises:  Candidate exam exercise list.
            threshold:  Level-4 structural overlap threshold (default 0.6 = 60%).
            window:     Level-4 comparison window size (default 50 recent exams).
        """
        if self.check_level_1(exercises):
            return True
        if self.check_level_2(exercises):
            return True
        if self.check_level_3(exercises):
            return True
        if self.check_level_4(exercises, threshold, window):
            return True
        return False


    # ── Diversity scoring ──────────────────────────────────────────────

    def compute_diversity_score(self, exercises: list[dict], window: int = 20) -> float:
        """
        Compute a diversity score in [0, 1] for a candidate exam.

            score = 1 - mean_jaccard(candidate_tids, last `window` registered exams)

        1.0 = completely novel (no overlap with recent exams)
        0.0 = identical template structure to all recent exams

        Args:
            exercises:  The candidate exam exercise list.
            window:     Number of recent past exams to compare against.
        """
        if not self.past_exams:
            return 1.0

        current_tids = set(ex.get("template_id", ex.get("id", "")) for ex in exercises)
        recent = self.past_exams[-window:]
        jaccards = []
        for past in recent:
            past_tids = set(past.get("template_ids", past.get("ids", [])))
            jaccards.append(_jaccard(current_tids, past_tids))

        mean_j = statistics.mean(jaccards) if jaccards else 0.0
        return round(1.0 - mean_j, 4)

    # ── Introspection ──────────────────────────────────────────────────

    def registry_size(self) -> int:
        return len(self.past_exams)

    def get_template_coverage(self) -> dict[str, int]:
        """Return a count of how many past exams used each template_id."""
        counts: dict[str, int] = {}
        for past in self.past_exams:
            for tid in past.get("template_ids", []):
                counts[tid] = counts.get(tid, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
