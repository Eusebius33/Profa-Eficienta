import random
import math
from bac_generator.generators.registry import registry
from bac_generator.generators.base import template

# ─────────────────────────────── Slot 5 ───────────────────────────────

@registry.register(slot=5)
@template("s1_midpoint_segment", "Geometrie analitică – mijlocul unui segment", "easy")
def gen_s1_ex5_midpoint(rng=random):
    x1 = rng.randint(-5, 5)
    x2 = x1 + 2 * rng.randint(-4, 4)
    y1 = rng.randint(-5, 5)
    y2 = y1 + 2 * rng.randint(-4, 4)
    mx = (x1 + x2) // 2
    my = (y1 + y2) // 2
    text = (f"Determinați coordonatele mijlocului segmentului $AB$, "
            f"unde $A({x1}, {y1})$ și $B({x2}, {y2})$.")
    solution = (f"$x_M = \\frac{{{x1}+{x2}}}{{2}} = {mx}$, "
                f"$y_M = \\frac{{{y1}+{y2}}}{{2}} = {my}$. Mijlocul: $M({mx}, {my})$.")
    return {"id": "s1_ex5_midpoint", "text": text, "solution": solution,
            "points": 5, "params": {"x1": x1, "x2": x2, "y1": y1, "y2": y2, "mx": mx, "my": my}, "lesson": "Numere complexe"}

@registry.register(slot=5)
@template("s1_parallel_line_through_point", "Dreapta paralelă prin un punct dat", "medium")
def gen_s1_ex5_parallel_line(rng=random):
    a = rng.choice([-3, -2, -1, 1, 2, 3])
    b = rng.choice([-2, -1, 1, 2])
    c = rng.randint(-10, 10)
    x1 = rng.randint(-3, 3)
    y1 = rng.randint(-3, 3)
    c_new = -(a*x1 + b*y1)
    text = (f"Determinați ecuația dreptei paralele cu $d: {a}x {b:+}y {c:+} = 0$ "
            f"ce trece prin $A({x1}, {y1})$.")
    solution = (f"Ecuația paralelei: ${a}x {b:+}y + c' = 0$. "
                f"Înlocuind $A$: ${a*x1 + b*y1} + c' = 0 \\Rightarrow c' = {c_new}$. "
                f"Ecuația: ${a}x {b:+}y {c_new:+} = 0$.")
    return {"id": "s1_ex5_parallel_line", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "x1": x1, "y1": y1, "c_new": c_new}, "lesson": "Trigonometrie"}

@registry.register(slot=5)
@template("s1_collinear_vectors_condition", "Condiția de coliniaritate a vectorilor", "medium")
def gen_s1_ex5_vectors(rng=random):
    c = rng.choice([2, 3])
    d = rng.choice([4, 5, 6])
    multiplier = rng.choice([2, 3])
    b = multiplier * d
    a = multiplier * c
    text = (f"Determinați $m \\in \\mathbb{{R}}$ pentru care $\\vec{{u}} = m\\vec{{i}} + {b}\\vec{{j}}$ "
            f"și $\\vec{{v}} = {c}\\vec{{i}} + {d}\\vec{{j}}$ sunt coliniari.")
    solution = (f"Coliniari ⟺ $\\frac{{m}}{{{c}}} = \\frac{{{b}}}{{{d}}} "
                f"\\Rightarrow {d}m = {b*c} \\Rightarrow m = {a}$.")
    return {"id": "s1_ex5_vectors", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "d": d}, "lesson": "Trigonometrie"}

@registry.register(slot=5)
@template("s1_line_equation_two_points", "Ecuația dreptei prin două puncte date", "easy")
def gen_s1_ex5_line_two_points(rng=random):
    x1 = rng.randint(-3, 0)
    y1 = rng.randint(-3, 0)
    x2 = rng.randint(1, 4)
    y2 = rng.randint(1, 4)
    dy = y2 - y1
    dx = x2 - x1
    # Line: dy*(x-x1) = dx*(y-y1)  → dy*x - dx*y - (dy*x1 - dx*y1) = 0
    c = -(dy*x1 - dx*y1)
    text = (f"Determinați ecuația dreptei care trece prin punctele $A({x1}, {y1})$ și $B({x2}, {y2})$.")
    solution = (f"Panta: $m = \\frac{{{y2}-({y1})}}{{{x2}-({x1})}} = \\frac{{{dy}}}{{{dx}}}$.\n"
                f"Ecuația: $y - ({y1}) = \\frac{{{dy}}}{{{dx}}}(x - ({x1}))$, "
                f"adică ${dy}x - {dx}y {c:+} = 0$.")
    return {"id": "s1_ex5_line_two_points", "text": text, "solution": solution,
            "points": 5, "params": {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "dy": dy, "dx": dx}, "lesson": "Trigonometrie"}

@registry.register(slot=5)
@template("s1_distance_point_to_line", "Distanța de la un punct la o dreaptă", "medium")
def gen_s1_ex5_distance(rng=random):
    a = rng.choice([3, 4, 5, 12])
    b = rng.choice([3, 4, 5, 12])
    c = rng.randint(-6, 6)
    x0 = rng.randint(-2, 2)
    y0 = rng.randint(-2, 2)
    dist_num = abs(a*x0 + b*y0 + c)
    dist_den = round(math.sqrt(a**2 + b**2), 4)
    text = (f"Calculați distanța de la punctul $P({x0}, {y0})$ la dreapta "
            f"$d: {a}x + {b}y {c:+} = 0$.")
    solution = (f"$d(P, d) = \\frac{{|{a} \\cdot ({x0}) + {b} \\cdot ({y0}) {c:+}|}}{{"
                f"\\sqrt{{{a}^2 + {b}^2}}}} = \\frac{{{dist_num}}}{{\\sqrt{{{a**2+b**2}}}}}$.")
    return {"id": "s1_ex5_distance", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "x0": x0, "y0": y0, "dist_num": dist_num}, "lesson": "Trigonometrie"}

def gen_s1_ex5(rng=random):
    return rng.choice(registry.get_generators(5))(rng)


# ─────────────────────────────── Slot 6 ───────────────────────────────

@registry.register(slot=6)
@template("s1_law_of_cosines", "Teorema cosinusului", "medium")
def gen_s1_ex6_law_cos(rng=random):
    triangle = rng.choice([
        {"b": 3, "c": 8, "cosA": "1/2", "cosA_val": 0.5, "a": 7},
        {"b": 5, "c": 8, "cosA": "1/2", "cosA_val": 0.5, "a": 7},
        {"b": 3, "c": 5, "cosA": "-1/2", "cosA_val": -0.5, "a": 7}
    ])
    b, c, cosA_str, cosA_val, a = triangle["b"], triangle["c"], triangle["cosA"], triangle["cosA_val"], triangle["a"]
    text = (f"Se consideră triunghiul $ABC$ cu $AB = {c}$, $AC = {b}$ și $\\cos A = {cosA_str}$. "
            f"Calculați $BC$.")
    solution = (f"$BC^2 = {c}^2 + {b}^2 - 2 \\cdot {c} \\cdot {b} \\cdot ({cosA_str}) = "
                f"{c**2 + b**2 - 2*b*c*cosA_val:.0f}$. Deci $BC = {a}$.")
    return {"id": "s1_ex6_law_cos", "text": text, "solution": solution,
            "points": 5, "params": {"b": b, "c": c, "cosA": cosA_str, "a": a}, "lesson": "Trigonometrie"}

@registry.register(slot=6)
@template("s1_triangle_area_formula", "Aria triunghiului cu sin", "easy")
def gen_s1_ex6_area(rng=random):
    AB = rng.choice([4, 6, 8, 12])
    AC = rng.randint(3, 8)
    area = (AB * AC) // 4
    text = (f"Calculați aria triunghiului $ABC$ cu $AB = {AB}$, $AC = {AC}$ și "
            f"$m(\\hat{{A}}) = 30^\\circ$.")
    solution = (f"$\\mathcal{{A}} = \\frac{{1}}{{2}} \\cdot {AB} \\cdot {AC} \\cdot \\sin 30^\\circ "
                f"= \\frac{{1}}{{2}} \\cdot {AB} \\cdot {AC} \\cdot \\frac{{1}}{{2}} = {area}$.")
    return {"id": "s1_ex6_area", "text": text, "solution": solution,
            "points": 5, "params": {"AB": AB, "AC": AC, "area": area}, "lesson": "Trigonometrie"}

@registry.register(slot=6)
@template("s1_trig_special_values", "Calcul cu valori trigonometrice remarcabile", "easy")
def gen_s1_ex6_trig_calc(rng=random):
    # Vary the expression to generate different problems each time
    variants = [
        ("2\\sin 30^\\circ - 2\\cos 60^\\circ + 4\\sin 90^\\circ", "2 \\cdot \\frac{1}{2} - 2 \\cdot \\frac{1}{2} + 4 \\cdot 1", "1 - 1 + 4", 4),
        ("4\\cos^2 45^\\circ + 2\\sin 30^\\circ - \\cos 180^\\circ", "4 \\cdot \\frac{1}{2} + 2 \\cdot \\frac{1}{2} - (-1)", "2 + 1 + 1", 4),
        ("\\tan 45^\\circ + \\cos 0^\\circ + 2\\sin 90^\\circ", "1 + 1 + 2 \\cdot 1", "1 + 1 + 2", 4),
        ("3\\cos 60^\\circ + 2\\sin 30^\\circ - \\sin 0^\\circ", "3 \\cdot \\frac{1}{2} + 2 \\cdot \\frac{1}{2} - 0", "\\frac{3}{2} + 1", 5),
        ("2\\cos^2 30^\\circ + \\sin^2 30^\\circ", "2 \\cdot \\frac{3}{4} + \\frac{1}{4}", "\\frac{6}{4} + \\frac{1}{4}", 2),
    ]
    expr, steps, simplified, result = rng.choice(variants)
    text = f"Arătați că $E = {expr}$ este număr natural."
    solution = (f"$E = {steps} = {simplified} = {result} \\in \\mathbb{{N}}$.")
    return {"id": "s1_ex6_trig_calc", "text": text, "solution": solution,
            "points": 5, "params": {"expr": expr, "result": result}, "lesson": "Trigonometrie"}

@registry.register(slot=6)
@template("s1_law_of_sines", "Teorema sinusurilor", "medium")
def gen_s1_ex6_law_sin(rng=random):
    R = rng.choice([3, 4, 5, 6])
    angle_deg = rng.choice([30, 45, 60])
    sin_val = {30: "1/2", 45: "\\frac{\\sqrt{2}}{2}", 60: "\\frac{\\sqrt{3}}{2}"}[angle_deg]
    sin_float = {30: 0.5, 45: 0.7071, 60: 0.8660}[angle_deg]
    a = round(2 * R * sin_float, 4)
    text = (f"În triunghiul $ABC$, $R = {R}$ (raza cercului circumscris) și $m(\\hat{{A}}) = {angle_deg}^\\circ$. "
            f"Calculați lungimea laturii $BC$.")
    solution = (f"Teorema sinusurilor: $\\frac{{BC}}{{\\sin A}} = 2R$.\n"
                f"$BC = 2 \\cdot {R} \\cdot \\sin {angle_deg}^\\circ = 2 \\cdot {R} \\cdot {sin_val} = {a}$.")
    return {"id": "s1_ex6_law_sin", "text": text, "solution": solution,
            "points": 5, "params": {"R": R, "angle_deg": angle_deg, "a": a}, "lesson": "Trigonometrie"}

@registry.register(slot=6)
@template("s1_trig_identity_simplification", "Simplificarea identităților trigonometrice", "hard")
def gen_s1_ex6_trig_identity(rng=random):
    variants = [
        (
            "\\sin^2 x + \\cos^2 x + \\tan^2 x - \\tan^2 x \\cdot \\sin^2 x",
            "1 + \\tan^2 x(1 - \\sin^2 x) = 1 + \\tan^2 x \\cdot \\cos^2 x = 1 + \\sin^2 x"
        ),
        (
            "\\frac{\\sin^2 x}{1-\\cos x} - 1",
            "\\frac{1-\\cos^2 x}{1-\\cos x} - 1 = (1+\\cos x) - 1 = \\cos x"
        ),
        (
            "(\\sin x + \\cos x)^2 + (\\sin x - \\cos x)^2",
            "\\sin^2 x + 2\\sin x \\cos x + \\cos^2 x + \\sin^2 x - 2\\sin x \\cos x + \\cos^2 x = 2"
        ),
        (
            "\\frac{1}{1+\\tan^2 x}",
            "\\frac{1}{\\sec^2 x} = \\cos^2 x"
        ),
        (
            "\\tan x \\cdot \\cos x - \\sin x + 2\\sin x",
            "\\frac{\\sin x}{\\cos x} \\cdot \\cos x - \\sin x + 2\\sin x = \\sin x - \\sin x + 2\\sin x = 2\\sin x"
        ),
    ]
    expr, sol = rng.choice(variants)
    text = f"Simplificați expresia $E = {expr}$."
    solution = f"$E = {sol}$."
    return {"id": "s1_ex6_trig_identity", "text": text, "solution": solution,
            "points": 5, "params": {"expr": expr}, "lesson": "Trigonometrie"}

def gen_s1_ex6(rng=random):
    return rng.choice(registry.get_generators(6))(rng)
