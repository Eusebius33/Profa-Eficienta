"""
Difficulty for the BAC generator: ușor / mediu / dificil / olimpic.

Every one of the 70 exercise templates takes exactly `rng` and draws its
parameters with randint/choice/randrange. So the primary channel is a proxy
RNG that *reweights* those draws - small, friendly integers at `usor`, larger
and uglier ones at `dificil` - without any template having to change.

TWO SAFETY RULES, both learned from real code in this repo:

1. NEVER shrink the support of a draw. generators/matrices.py:46-50 is
   rejection sampling:

       k = rng.randint(1, 3); m = rng.randint(2, 4); n = rng.randint(2, 4)
       while m == k: m = rng.randint(2, 4)
       while n in (k, m): n = rng.randint(2, 4)

   With k=3, m=4 the only value n may take is 2. If a biased randint ever gave
   2 probability zero, that loop would spin forever and hang a web request.
   The reweighting below is a monotone transform of a uniform variate, so every
   value in [a, b] keeps strictly positive probability.

2. NEVER reorder or filter a choice() sequence. generators/algebra.py picks
   Pythagorean triples and matrices.py derives dependent values from the chosen
   element, so biasing the index is safe but touching the contents would
   produce wrong mathematics.

Determinism survives because every draw still comes from the same underlying
random.Random - seeding the generator reproduces the exam exactly as before.
"""

import inspect
import random

# The levels the UI offers, in order.
LEVELS = ("usor", "mediu", "dificil", "olimpic")
DEFAULT_LEVEL = "mediu"

LEVEL_LABELS = {
    "usor":    "Ușor",
    "mediu":   "Mediu",
    "dificil": "Dificil",
    "olimpic": "Olimpic",
}

# olimpic is NOT a BAC level. Nothing in the 217-paper corpus is olympiad work,
# so a paper generated at this level is synthesised above the syllabus and must
# say so on screen and in the PDF.
ABOVE_BAC = frozenset({"olimpic"})
ABOVE_BAC_NOTE = "Peste nivel BAC — exerciții de antrenament, nu o variantă oficială."

# How hard each level pulls. Negative pulls draws toward the low end of a
# range, positive toward the high end; 0 leaves the distribution untouched, so
# "mediu" reproduces today's output exactly.
_BIAS = {"usor": -1.0, "mediu": 0.0, "dificil": 0.9, "olimpic": 1.0}

# Which levels a template is suitable for, derived from the static
# easy/medium/hard string it already carries. That field has been dead weight
# since it was introduced - this gives it a job instead of deleting it.
_BANDS_FROM_STATIC = {
    "easy":   ("usor", "mediu"),
    "medium": ("usor", "mediu", "dificil"),
    "hard":   ("mediu", "dificil", "olimpic"),
}


def normalize_level(level):
    """Accept whatever the form posted; fall back to mediu."""
    if not level:
        return DEFAULT_LEVEL
    key = str(level).strip().lower()
    # tolerate the diacritic spelling and the legacy English words
    key = key.replace("ș", "s").replace("ş", "s").replace("ț", "t").replace("ţ", "t")
    aliases = {"easy": "usor", "medium": "mediu", "hard": "dificil", "olympic": "olimpic"}
    key = aliases.get(key, key)
    return key if key in LEVELS else DEFAULT_LEVEL


def bands_for_static(static_difficulty):
    return _BANDS_FROM_STATIC.get(str(static_difficulty or "medium").lower(),
                                  _BANDS_FROM_STATIC["medium"])


def _skew(u, bias):
    """Map a uniform u in [0,1) to a biased value in [0,1).

    Monotone and onto, so no outcome is ever excluded - which is what keeps the
    rejection-sampling loops in matrices.py terminating.
    """
    if bias == 0.0:
        return u
    exponent = 1.0 + abs(bias)
    return u ** exponent if bias < 0 else 1.0 - (1.0 - u) ** exponent


class DifficultyRNG:
    """A random.Random work-alike that leans its draws toward easier or harder
    parameter values. Anything it does not implement is delegated untouched."""

    def __init__(self, rng, level=DEFAULT_LEVEL):
        self._rng = rng
        self.level = normalize_level(level)
        self._bias = _BIAS[self.level]

    # ── biased draws ──────────────────────────────────────────────────
    def randint(self, a, b):
        if b <= a or self._bias == 0.0:
            return self._rng.randint(a, b)
        span = b - a + 1
        index = int(_skew(self._rng.random(), self._bias) * span)
        return a + min(index, span - 1)

    def randrange(self, start, stop=None, step=1):
        if stop is None:
            start, stop = 0, start
        if step != 1 or self._bias == 0.0:
            return self._rng.randrange(start, stop, step)
        return self.randint(start, stop - 1)

    def choice(self, seq):
        items = list(seq)
        if not items:
            return self._rng.choice(seq)
        if self._bias == 0.0 or len(items) == 1:
            return self._rng.choice(items)
        # Bias the index only. The order of the sequence is the author's and
        # dependent values are derived from the element picked, so the contents
        # must never be reordered or filtered.
        index = int(_skew(self._rng.random(), self._bias) * len(items))
        return items[min(index, len(items) - 1)]

    def uniform(self, a, b):
        if self._bias == 0.0:
            return self._rng.uniform(a, b)
        return a + _skew(self._rng.random(), self._bias) * (b - a)

    # ── everything else is the underlying generator ───────────────────
    def random(self):
        return self._rng.random()

    def shuffle(self, seq):
        return self._rng.shuffle(seq)

    def sample(self, population, k, **kwargs):
        return self._rng.sample(population, k, **kwargs)

    def __getattr__(self, name):
        return getattr(self._rng, name)


def wrap(rng, level):
    """A plain Random at `mediu`, so the default path is bit-for-bit unchanged."""
    level = normalize_level(level)
    return rng if level == DEFAULT_LEVEL else DifficultyRNG(rng, level)


def accepts_difficulty(func):
    """True when a template opted in to real structural control by declaring a
    `difficulty` parameter. Checked once at decoration time."""
    try:
        return "difficulty" in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def template_bands(func):
    """The levels a registered template declares itself suitable for."""
    declared = getattr(func, "bands", None)
    if declared:
        return tuple(declared)
    return bands_for_static(getattr(func, "difficulty", "medium"))


def suitable(funcs, level):
    """Templates usable at `level`, or all of them when that would leave a slot
    with nothing to draw - an empty slot is worse than an off-level exercise,
    and coverage.py reports the compromise."""
    level = normalize_level(level)
    matching = [f for f in funcs if level in template_bands(f)]
    return matching or list(funcs)
