"""
ExerciseTemplate decorator for the BAC Generator.

Separates mathematical template identity from parameter generation.
Every registered generator function should be decorated with @template(...)
to gain:
  - template_id:       stable string ID for this mathematical structure
  - topic:             Romanian curriculum topic name
  - difficulty:        "easy", "medium", or "hard"
  - param_signature:   deterministic fingerprint of the parameters generated
  - topic, difficulty: passed through to exercise metadata

Usage:
    @registry.register(slot=1)
    @template(template_id="prog_arith_nth_term", topic="Progresii aritmetice", difficulty="easy")
    def gen_s1_ex1_prog_arith(rng=random):
        ...  # unchanged body

Adding a new template variant only requires a new decorated function.
No changes to the registry or generator pipeline.
"""
import functools
import random
import re

from bac_generator.generators import difficulty as difficulty_mod


# Templates build expressions by string interpolation, so a coefficient that
# happens to come out as 1 or 0 is printed literally: "f(x) = x^2 +0x +3",
# "P(X) = X^3 - 1X - 4", "3^{1x +0} = 81". Measured over 2190 generated
# exercises, roughly one in six carried at least one of these. Tidying the
# rendered string in one place beats editing two dozen templates, and it
# cannot change the mathematics - only how it is written.
_TIDY_RULES = (
    # a zero term disappears: "+ 0x", "- 0x^2"
    (re.compile(r"\s*[+-]\s*0[a-zA-Z](?:\^\{?\d+\}?)?(?![\w^])"), ""),
    # a trailing "+ 0" / "- 0" adds nothing
    (re.compile(r"\s*[+-]\s*0(?![\d.\w])"), ""),
    # an explicit coefficient of 1 is never written: "1x" -> "x".
    # The lookbehind protects indices (a_1x) and longer numbers (21x).
    (re.compile(r"(?<![\d._])1(?=[a-zA-Z])"), ""),
    # signs left adjacent by the rules above
    (re.compile(r"\+\s*-\s*"), " - "),
    (re.compile(r"-\s*\+\s*"), " - "),
    # and the whitespace they leave behind
    (re.compile(r"[ \t]{2,}"), " "),
)


def tidy_expression(text):
    """Remove 1-coefficients and 0-terms from a rendered statement."""
    if not text:
        return text
    for pattern, replacement in _TIDY_RULES:
        text = pattern.sub(replacement, text)
    return text


def template(template_id: str, topic: str, difficulty: str = "medium", *, bands=None):
    """
    Decorator that injects template metadata into an exercise generator function.

    Args:
        template_id:  Stable, unique string identifier for this mathematical template.
                      Convention: "slot_concept_variant", e.g. "s1_arith_seq_nth_term"
        topic:        Human-readable Romanian curriculum topic.
        difficulty:   "easy", "medium", or "hard". Seeds `bands` when that is
                      not given explicitly - see generators/difficulty.py.
        bands:        Which of ușor/mediu/dificil/olimpic this template suits.
                      Optional; derived from `difficulty` when omitted.

    The decorated function must accept `rng` as its first argument and return an
    exercise dict with at least {"text", "solution", "points", "params", "lesson"}.
    The decorator will add:
        exercise["template_id"]      = template_id
        exercise["topic"]            = topic
        exercise["difficulty"]       = difficulty
        exercise["param_signature"]  = deterministic fingerprint of params dict
    """
    def decorator(func):
        # Computed once, not per call: a template opts into structural control
        # by declaring `difficulty`. The other 69 are called exactly as before.
        takes_difficulty = difficulty_mod.accepts_difficulty(func)

        @functools.wraps(func)
        def wrapper(rng=random, difficulty=None):
            level = difficulty_mod.normalize_level(difficulty)
            result = func(rng, difficulty=level) if takes_difficulty else func(rng)

            # Written form only; the maths is untouched.
            for field in ("text", "solution"):
                if result.get(field):
                    result[field] = tidy_expression(result[field])

            # Inject template metadata
            result["template_id"] = template_id
            result["topic"] = topic
            result["difficulty"] = difficulty

            # Build deterministic param_signature from the exercise params
            params = result.get("params", {})
            sig_parts = []
            for k in sorted(params.keys()):
                v = params[k]
                if isinstance(v, float):
                    v = round(v, 4)
                sig_parts.append(f"{k}={v}")
            result["param_signature"] = ";".join(sig_parts)

            return result

        # Expose metadata on the function itself for introspection
        wrapper.template_id = template_id
        wrapper.topic = topic
        wrapper.difficulty = difficulty
        wrapper.bands = tuple(bands) if bands else difficulty_mod.bands_for_static(difficulty)
        wrapper.takes_difficulty = takes_difficulty
        return wrapper

    return decorator
