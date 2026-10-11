"""
Subiect II, problema 2: polynomials.

Measured over 217 official papers, problem 2 of Subiect II is a polynomial in
roughly a third of them (M1 35%, M3 32%, M2 28%) and a composition law in
roughly a quarter. The generator could only ever produce the composition law,
so a third of real Subiect II papers had no counterpart here at all.

These follow the shape the corpus uses: a parametric cubic or quartic, then
a) a value or a root, b) something about the division or the parameter,
c) a symmetric-function identity in the roots - each worth 5p.
"""

import random

from bac_generator.generators.base import template
from bac_generator.generators.registry import registry


def _fmt(coefficient, symbol, first=False):
    """Render one term of a polynomial with a readable sign."""
    if coefficient == 0:
        return ""
    sign = "" if first and coefficient > 0 else (" + " if coefficient > 0 else " - ")
    magnitude = abs(coefficient)
    body = symbol if magnitude == 1 and symbol else f"{magnitude}{symbol}"
    return f"{sign}{body}"


@registry.register(slot=8)
@template("s2_poly_root_viete", "Polinoame – rădăcină dată și relațiile lui Viète", "hard")
def gen_s2_ex2_poly_viete(rng=random):
    """f = (X-1)(X-r2)(X-r3), built from its roots rather than from random
    coefficients.

    Drawing a, b, c at random and forcing f(1)=0 does give a valid polynomial,
    but two of its roots are complex most of the time, and then c) asks for a
    sum of squares that comes out negative. That is a correct answer to a
    question no tehnologic candidate should be asked. Choosing integer roots
    first keeps the arithmetic inside the syllabus and needs no resampling.
    """
    r2 = rng.choice([-4, -3, -2, -1, 2, 3, 4])
    r3 = rng.choice([-3, -2, 2, 3, 5])

    # (X - 1)(X - r2)(X - r3) = X^3 + aX^2 + bX + c
    a = -(1 + r2 + r3)
    b = r2 * r3 + r2 + r3
    c = -(r2 * r3)
    sum_all = 1 + r2 + r3
    sum_sq = 1 + r2 ** 2 + r3 ** 2

    poly = "X^3" + _fmt(a, "X^2") + _fmt(b, "X") + _fmt(c, "")
    quotient = "X^2" + _fmt(-(r2 + r3), "X") + _fmt(r2 * r3, "")
    text = (
        f"Se consideră polinomul $f = {poly}$, cu rădăcinile $x_1$, $x_2$, $x_3$.\n\n"
        f"a) Arătați că $f(1) = 0$.\n\n"
        f"b) Determinați câtul împărțirii lui $f$ la $X - 1$.\n\n"
        f"c) Calculați $x_1^2 + x_2^2 + x_3^2$."
    )
    solution = (
        f"a) $f(1) = 1 + ({a}) + ({b}) + ({c}) = 0$.\n\n"
        f"b) Prin schema lui Horner, câtul este ${quotient}$, "
        f"cu rădăcinile ${r2}$ și ${r3}$.\n\n"
        f"c) Din relațiile lui Viète: $x_1 + x_2 + x_3 = {sum_all}$ și "
        f"$x_1x_2 + x_1x_3 + x_2x_3 = {b}$, deci "
        f"$x_1^2 + x_2^2 + x_3^2 = ({sum_all})^2 - 2\\cdot({b}) = {sum_sq}$."
    )
    return {
        "id": "s2_ex2_poly_viete", "text": text, "solution": solution,
        "points": 15,
        "params": {"r2": r2, "r3": r3, "a": a, "b": b, "c": c, "sum_sq": sum_sq},
        "lesson": "Polinoame",
    }


@registry.register(slot=8)
@template("s2_poly_parameter_remainder", "Polinoame – parametru determinat din rest", "hard")
def gen_s2_ex2_poly_remainder(rng=random):
    """f = mX^3 + pX^2 - mX - p, which vanishes at 1 for every m."""
    p = rng.choice([2, 3, 4, 5])
    divisor = rng.choice([2, 3])
    m_target = rng.choice([1, 2, 3])
    # remainder of f at X + divisor
    rest = m_target * (-divisor) ** 3 + p * divisor ** 2 + m_target * divisor - p

    text = (
        f"Se consideră polinomul $f = mX^3 + {p}X^2 - mX - {p}$, "
        f"unde $m$ este număr real nenul.\n\n"
        f"a) Arătați că $f(1) = 0$, pentru orice număr real nenul $m$.\n\n"
        f"b) Pentru $m = {m_target}$, determinați restul împărțirii lui $f$ "
        f"la $g = X + {divisor}$.\n\n"
        f"c) Determinați $m$ pentru care $f$ este divizibil cu $X + 1$."
    )
    solution = (
        f"a) $f(1) = m + {p} - m - {p} = 0$, independent de $m$.\n\n"
        f"b) Restul este $f(-{divisor}) = {rest}$.\n\n"
        f"c) $f(-1) = -m + {p} + m - {p} = 0$ pentru orice $m$, "
        f"deci $f$ este divizibil cu $X + 1$ pentru orice $m$ nenul."
    )
    return {
        "id": "s2_ex2_poly_remainder", "text": text, "solution": solution,
        "points": 15, "params": {"p": p, "divisor": divisor, "m": m_target, "rest": rest},
        "lesson": "Polinoame",
    }


@registry.register(slot=8)
@template("s2_poly_biquadratic", "Polinoame – ecuație bipătratică și suma rădăcinilor", "hard")
def gen_s2_ex2_poly_biquadratic(rng=random):
    """f = X^4 - sX^2 + p, factorising as (X^2 - u)(X^2 - v)."""
    u = rng.choice([1, 4, 9])
    v = rng.choice([1, 4, 16])
    s = u + v
    p = u * v
    sum_sq = 2 * (u + v)                  # x1^2 + ... + x4^2 = 2(u + v)

    text = (
        f"Se consideră polinomul $f = X^4 - {s}X^2 + {p}$, "
        f"cu rădăcinile $x_1$, $x_2$, $x_3$, $x_4$.\n\n"
        f"a) Arătați că $f = (X^2 - {u})(X^2 - {v})$.\n\n"
        f"b) Determinați rădăcinile reale ale polinomului $f$.\n\n"
        f"c) Calculați $x_1^2 + x_2^2 + x_3^2 + x_4^2$."
    )
    roots = sorted({u, v})
    root_text = ", ".join(
        f"$\\pm\\sqrt{{{r}}}$" if int(r ** 0.5) ** 2 != r else f"$\\pm{int(r ** 0.5)}$"
        for r in roots
    )
    solution = (
        f"a) $(X^2 - {u})(X^2 - {v}) = X^4 - {s}X^2 + {p} = f$.\n\n"
        f"b) $X^2 = {u}$ sau $X^2 = {v}$, deci rădăcinile sunt {root_text}.\n\n"
        f"c) Suma pătratelor rădăcinilor este "
        f"$2({u} + {v}) = {sum_sq}$."
    )
    return {
        "id": "s2_ex2_poly_biquadratic", "text": text, "solution": solution,
        "points": 15, "params": {"u": u, "v": v, "s": s, "p": p},
        "lesson": "Polinoame",
    }
