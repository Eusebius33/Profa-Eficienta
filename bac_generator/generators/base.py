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


def template(template_id: str, topic: str, difficulty: str = "medium"):
    """
    Decorator that injects template metadata into an exercise generator function.

    Args:
        template_id:  Stable, unique string identifier for this mathematical template.
                      Convention: "slot_concept_variant", e.g. "s1_arith_seq_nth_term"
        topic:        Human-readable Romanian curriculum topic.
        difficulty:   "easy", "medium", or "hard".

    The decorated function must accept `rng` as its first argument and return an
    exercise dict with at least {"text", "solution", "points", "params", "lesson"}.
    The decorator will add:
        exercise["template_id"]      = template_id
        exercise["topic"]            = topic
        exercise["difficulty"]       = difficulty
        exercise["param_signature"]  = deterministic fingerprint of params dict
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(rng=random):
            result = func(rng)

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
        return wrapper

    return decorator
