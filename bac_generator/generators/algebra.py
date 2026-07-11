import random
import math
from bac_generator.generators.registry import registry
from bac_generator.generators.base import template

# ─────────────────────────────── Slot 1 ───────────────────────────────

@registry.register(slot=1)
@template("s1_arith_seq_nth_term", "Progresii aritmetice", "easy")
def gen_s1_ex1_prog_arith(rng=random):
    a1 = rng.randint(1, 10)
    d  = rng.randint(2, 6)
    n  = rng.randint(4, 8)
    an = a1 + (n - 1) * d
    text = (f"Determinați al ${n}$-lea termen al progresiei aritmetice $(a_n)_{{n \\geq 1}}$, "
            f"știind că $a_1 = {a1}$ și rația $d = {d}$.")
    solution = (f"Termenul al ${n}$-lea se calculează după formula $a_{{{n}}} = a_1 + ({n}-1)d$.\n"
                f"Înlocuind: $a_{{{n}}} = {a1} + {n-1} \\cdot {d} = {a1} + {(n-1)*d} = {an}$.")
    return {"id": "s1_ex1_prog_arith", "text": text, "solution": solution,
            "points": 5, "params": {"a1": a1, "d": d, "n": n, "an": an}, "lesson": "Progresii"}

@registry.register(slot=1)
@template("s1_geom_seq_nth_term", "Progresii geometrice", "easy")
def gen_s1_ex1_prog_geom(rng=random):
    b1 = rng.randint(1, 4)
    q  = rng.choice([2, 3])
    n  = rng.randint(3, 5)
    bn = b1 * (q ** (n - 1))
    text = (f"Determinați al ${n}$-lea termen al progresiei geometrice $(b_n)_{{n \\geq 1}}$, "
            f"știind că $b_1 = {b1}$ și rația $q = {q}$.")
    solution = (f"Formula termenului general: $b_{{{n}}} = b_1 \\cdot q^{{{n-1}}}$.\n"
                f"Înlocuind: $b_{{{n}}} = {b1} \\cdot {q}^{{{n-1}}} = {b1} \\cdot {q**(n-1)} = {bn}$.")
    return {"id": "s1_ex1_prog_geom", "text": text, "solution": solution,
            "points": 5, "params": {"b1": b1, "q": q, "n": n, "bn": bn}, "lesson": "Progresii"}

@registry.register(slot=1)
@template("s1_radical_integer", "Calcul cu radicali", "easy")
def gen_s1_ex1_calc(rng=random):
    a = rng.randint(2, 5)
    b = rng.choice([2, 3, 5, 6, 7])
    val = a**2 + b
    text = f"Arătați că numărul $N = ({a} - \\sqrt{{{b}}})^2 + {2*a}\\sqrt{{{b}}}$ este număr întreg."
    solution = (f"$(a-b)^2 = a^2 - 2ab + b^2$:\n"
                f"$({a} - \\sqrt{{{b}}})^2 = {a**2} - {2*a}\\sqrt{{{b}}} + {b}$.\n"
                f"Deci $N = {a**2} - {2*a}\\sqrt{{{b}}} + {b} + {2*a}\\sqrt{{{b}}} = {val}$ ∈ ℤ.")
    return {"id": "s1_ex1_calc", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "val": val}, "lesson": "Radicali"}

@registry.register(slot=1)
@template("s1_arith_seq_sum", "Progresii aritmetice – suma primilor n termeni", "medium")
def gen_s1_ex1_arith_sum(rng=random):
    a1 = rng.randint(1, 5)
    d  = rng.randint(1, 4)
    n  = rng.choice([5, 6, 8, 10])
    an = a1 + (n - 1) * d
    sn = n * (a1 + an) // 2
    text = (f"Calculați suma primilor ${n}$ termeni ai progresiei aritmetice cu $a_1 = {a1}$ și $d = {d}$.")
    solution = (f"Ultimul termen: $a_{{{n}}} = {a1} + {n-1} \\cdot {d} = {an}$.\n"
                f"Suma: $S_{{{n}}} = \\frac{{{n}(a_1 + a_{{{n}}})}}{2} = \\frac{{{n} \\cdot ({a1}+{an})}}{2} = {sn}$.")
    return {"id": "s1_ex1_arith_sum", "text": text, "solution": solution,
            "points": 5, "params": {"a1": a1, "d": d, "n": n, "sn": sn}, "lesson": "Progresii"}

@registry.register(slot=1)
@template("s1_radical_simplify", "Simplificarea expresiilor cu radicali", "medium")
def gen_s1_ex1_radical_simplify(rng=random):
    a = rng.randint(2, 6)
    b = rng.choice([2, 3, 5])
    expr_val = a**2 * b
    text = (f"Simplificați expresia $E = \\sqrt{{{expr_val}}} - {a-1}\\sqrt{{{b}}} + {a+1}\\sqrt{{{b}}}$.")
    solution = (f"$\\sqrt{{{expr_val}}} = \\sqrt{{{a**2} \\cdot {b}}} = {a}\\sqrt{{{b}}}$.\n"
                f"$E = {a}\\sqrt{{{b}}} - {a-1}\\sqrt{{{b}}} + {a+1}\\sqrt{{{b}}} = ({a} - {a-1} + {a+1})\\sqrt{{{b}}} = {a+2}\\sqrt{{{b}}}$.")
    return {"id": "s1_ex1_radical_simplify", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "expr_val": expr_val}, "lesson": "Radicali"}

@registry.register(slot=1)
@template("s1_complex_modulus", "Modulul unui număr complex", "easy")
def gen_s1_ex1_complex_modulus(rng=random):
    a, b, mod_val = rng.choice([(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (9, 12, 15), (7, 24, 25)])
    a = a * rng.choice([1, -1])
    b = b * rng.choice([1, -1])
    text = f"Se consideră numărul complex $z = {a} {b:+}i$. Calculați $|z|$."
    solution = (f"$|z| = \\sqrt{{{a}^2 + ({b})^2}} = \\sqrt{{{a**2} + {b**2}}} = "
                f"\\sqrt{{{a**2+b**2}}} = {mod_val}$.")
    return {"id": "s1_ex1_complex_modulus", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "mod_val": mod_val}, "lesson": "Numere complexe"}

@registry.register(slot=1)
@template("s1_complex_conjugate_product", "Conjugatul și produsul numerelor complexe", "medium")
def gen_s1_ex1_complex_conjugate(rng=random):
    a = rng.randint(1, 6)
    b = rng.randint(1, 6)
    prod = a**2 + b**2
    text = (f"Se consideră numărul complex $z = {a} + {b}i$ și conjugatul său $\\bar{{z}}$. "
            f"Arătați că $z \\cdot \\bar{{z}} = {prod}$.")
    solution = (f"$\\bar{{z}} = {a} - {b}i$.\n"
                f"$z \\cdot \\bar{{z}} = ({a}+{b}i)({a}-{b}i) = {a}^2 - ({b}i)^2 = {a**2} + {b**2} = {prod}$.")
    return {"id": "s1_ex1_complex_conjugate", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "prod": prod}, "lesson": "Numere complexe"}

@registry.register(slot=1)
@template("s1_complex_arithmetic", "Operații cu numere complexe", "medium")
def gen_s1_ex1_complex_arith(rng=random):
    a = rng.randint(1, 5)
    b = rng.randint(1, 5)
    c = rng.randint(1, 4)
    d = rng.randint(1, 4)
    # z1 = a+bi, z2 = c+di
    sum_re, sum_im = a + c, b + d
    prod_re = a*c - b*d
    prod_im = a*d + b*c
    sum_str = f"{sum_re} + {sum_im}i" if sum_im >= 0 else f"{sum_re} - {-sum_im}i"
    prod_im_str = f"{prod_im:+}i"
    text = (f"Se dau numerele complexe $z_1 = {a} + {b}i$ și $z_2 = {c} + {d}i$.\n\n"
            f"a) Calculați $z_1 + z_2$.\n\n"
            f"b) Calculați $z_1 \\cdot z_2$.\n\n"
            f"c) Calculați $|z_1|$.")
    mod1 = math.isqrt(a**2 + b**2)
    mod1_str = f"\\sqrt{{{a**2 + b**2}}}" if a**2 + b**2 != mod1**2 else str(mod1)
    solution = (f"a) $z_1 + z_2 = ({a}+{c}) + ({b}+{d})i = {sum_str}$.\n\n"
                f"b) $z_1 \\cdot z_2 = ({a}+{b}i)({c}+{d}i) = "
                f"{a*c} + {a*d}i + {b*c}i + {b*d}i^2 = {prod_re} {prod_im_str}$.\n\n"
                f"c) $|z_1| = \\sqrt{{{a}^2 + {b}^2}} = {mod1_str}$.")
    return {"id": "s1_ex1_complex_arith", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "d": d}, "lesson": "Numere complexe"}

@registry.register(slot=1)
@template("s1_geom_seq_sum", "Progresii geometrice – suma primilor n termeni", "medium")
def gen_s1_ex1_geom_sum(rng=random):
    b1 = rng.randint(1, 3)
    q  = rng.choice([2, 3])
    n  = rng.choice([4, 5, 6])
    sn = b1 * (q**n - 1) // (q - 1)
    text = (f"Calculați suma primilor ${n}$ termeni ai progresiei geometrice "
            f"$(b_n)_{{n \\geq 1}}$ cu $b_1 = {b1}$ și rația $q = {q}$.")
    solution = (f"Formula sumei: $S_{{{n}}} = b_1 \\cdot \\dfrac{{q^{{{n}}} - 1}}{{q - 1}} = "
                f"{b1} \\cdot \\dfrac{{{q}^{{{n}}} - 1}}{{{q} - 1}} = "
                f"{b1} \\cdot \\dfrac{{{q**n} - 1}}{{{q - 1}}} = "
                f"{b1} \\cdot \\dfrac{{{q**n - 1}}}{{{q-1}}} = {sn}$.")
    return {"id": "s1_ex1_geom_sum", "text": text, "solution": solution,
            "points": 5, "params": {"b1": b1, "q": q, "n": n, "sn": sn}, "lesson": "Progresii"}

def gen_s1_ex1(rng=random):
    return rng.choice(registry.get_generators(1))(rng)


# ─────────────────────────────── Slot 2 ───────────────────────────────

@registry.register(slot=2)
@template("s1_parabola_vertex", "Funcții de gradul al doilea – vertex", "easy")
def gen_s1_ex2_parabola_vertex(rng=random):
    m = rng.randint(-4, 4)
    k = rng.randint(1, 5)
    b = -2 * m
    c = m**2 + k
    text = (f"Determinați coordonatele vârfului parabolei $f(x) = x^2 {b:+}x {c:+}$.")
    solution = (f"$x_V = -\\frac{{b}}{{2a}} = -\\frac{{{b}}}{{2}} = {m}$,\n"
                f"$y_V = f({m}) = {m}^2 {b:+}({m}) {c:+} = {k}$.\n"
                f"Vârful: $V({m}, {k})$.")
    return {"id": "s1_ex2_parabola_vertex", "text": text, "solution": solution,
            "points": 5, "params": {"m": m, "k": k, "b": b, "c": c}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_func_graph_intersection", "Intersecția graficelor a două funcții", "medium")
def gen_s1_ex2_func_intersect(rng=random):
    x1 = rng.randint(-2, 1)
    x2 = rng.randint(2, 4)
    c  = rng.randint(1, 3)
    d  = rng.randint(-3, 3)
    b  = x1*x2 + d
    a  = x1 + x2 - c
    text = (f"Determinați abscisele punctelor de intersecție ale graficelor $f(x) = x^2 {-a:+}x {b:+}$ "
            f"și $g(x) = {c}x {d:+}$.")
    solution = (f"$f(x)=g(x) \\Rightarrow x^2 {-a-c:+}x {b-d:+} = 0$.\n"
                f"$\\Delta = {(-a-c)**2 - 4*(b-d)}$. Soluții: $x_1 = {x1}$, $x_2 = {x2}$.")
    return {"id": "s1_ex2_func_intersect", "text": text, "solution": solution,
            "points": 5, "params": {"x1": x1, "x2": x2, "a": a, "b": b, "c": c, "d": d}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_func_zero_product", "Zero-produs la funcții liniare", "easy")
def gen_s1_ex2_func_product(rng=random):
    a = rng.randint(2, 8)
    text = (f"Se consideră $f(x) = x - {a}$. Calculați produsul $P = f(1) \\cdot f(2) \\cdots f(10)$.")
    solution = (f"$f({a}) = {a} - {a} = 0$, deci $P = 0$.")
    return {"id": "s1_ex2_func_product", "text": text, "solution": solution,
            "points": 5, "params": {"a": a}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_quadratic_roots_vieta", "Suma și produsul rădăcinilor – relațiile lui Viète", "medium")
def gen_s1_ex2_vieta(rng=random):
    x1 = rng.randint(-4, -1)
    x2 = rng.randint(1, 5)
    s = x1 + x2
    p = x1 * x2
    b = -s
    c = p
    text = (f"Fie ecuația $x^2 {b:+}x {c:+} = 0$. Fără a rezolva ecuația, calculați $x_1^2 + x_2^2$.")
    solution = (f"Prin relațiile lui Viète: $x_1 + x_2 = {s}$, $x_1 x_2 = {p}$.\n"
                f"$x_1^2 + x_2^2 = (x_1+x_2)^2 - 2x_1 x_2 = {s}^2 - 2({p}) = {s**2} - {2*p} = {s**2 - 2*p}$.")
    return {"id": "s1_ex2_vieta", "text": text, "solution": solution,
            "points": 5, "params": {"x1": x1, "x2": x2, "b": b, "c": c, "s2": s**2-2*p}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_func_monotonicity_sign", "Semn și monotonie funcție liniară/pătratică", "easy")
def gen_s1_ex2_monotonicity(rng=random):
    m = rng.randint(1, 5)
    n = rng.randint(-3, -1)
    text = (f"Studiaţi monotonia funcţiei $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = {m}x {n:+}$.")
    solution = (f"$f$ este de forma $f(x) = ax + b$ cu $a = {m} \\gt 0$.\n"
                f"O funcție liniară cu $a \\gt 0$ este strict crescătoare pe $\\mathbb{{R}}$.")
    return {"id": "s1_ex2_monotonicity", "text": text, "solution": solution,
            "points": 5, "params": {"m": m, "n": n}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_func_composition", "Compoziția a două funcții", "medium")
def gen_s1_ex2_composition(rng=random):
    a = rng.randint(1, 4)
    b = rng.randint(-3, 3)
    c = rng.randint(1, 3)
    # f(x) = ax + b, g(x) = x^2 + c
    # fog(x) = f(g(x)) = a(x^2+c)+b = ax^2 + ac+b
    ac_b = a * c + b
    text = (f"Se consideră $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = {a}x {b:+}$ și "
            f"$g: \\mathbb{{R}} \\to \\mathbb{{R}}$, $g(x) = x^2 {c:+}$.\n\n"
            f"a) Calculați $(f \\circ g)(x)$.\n\n"
            f"b) Calculați $(f \\circ g)(1)$.\n\n"
            f"c) Rezolvați ecuația $(f \\circ g)(x) = f(x)$.")
    fog_1 = a * (1 + c) + b
    # fog(x) = ax^2 + ac+b; f(x) = ax+b
    # ax^2 + ac+b = ax+b => ax^2 - ax + ac = 0 => x^2 - x + c = 0
    disc = 1 - 4 * c
    if disc < 0:
        sol_c = "Nu are soluții reale ($\\Delta < 0$)."
    elif disc == 0:
        sol_c = f"$x = \\frac{{1}}{{2}}$."
    else:
        import math
        sol_c = f"$\\Delta = {disc}$, $x = \\frac{{1 \\pm \\sqrt{{{disc}}}}}{{2}}$."
    solution = (f"a) $(f \\circ g)(x) = f(g(x)) = {a}(x^2 {c:+}) {b:+} = {a}x^2 {ac_b:+}$.\n\n"
                f"b) $(f \\circ g)(1) = {a} \\cdot 1 {ac_b:+} = {a + ac_b}$.\n\n"
                f"c) ${a}x^2 {ac_b:+} = {a}x {b:+} \\Rightarrow {a}x^2 - {a}x {a*c:+} = 0 "
                f"\\Rightarrow x^2 - x {c:+} = 0$. {sol_c}")
    return {"id": "s1_ex2_composition", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "fog_1": fog_1}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_func_inverse", "Funcția inversă", "medium")
def gen_s1_ex2_inverse(rng=random):
    a = rng.choice([2, 3, 4, 5])
    b = rng.randint(-4, 4)
    # f(x) = ax + b; f_inv(x) = (x-b)/a
    text = (f"Se consideră $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = {a}x {b:+}$.\n\n"
            f"a) Arătați că $f$ este bijectivă.\n\n"
            f"b) Determinați $f^{{-1}}(x)$.\n\n"
            f"c) Calculați $f^{{-1}}({a + b})$.")
    inv_val = 1  # f(1) = a + b, so f_inv(a+b) = 1
    solution = (f"a) $f$ este liniară cu $a = {a} \\neq 0$, deci este bijectivă.\n\n"
                f"b) $y = {a}x {b:+} \\Rightarrow x = \\frac{{y {-b:+}}}{{{a}}}$. "
                f"Deci $f^{{-1}}(x) = \\frac{{x {-b:+}}}{{{a}}}$.\n\n"
                f"c) $f^{{-1}}({a + b}) = \\frac{{{a + b} {-b:+}}}{{{a}}} = \\frac{{{a}}}{{{a}}} = 1$.")
    return {"id": "s1_ex2_inverse", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "val": a + b, "inv_val": inv_val}, "lesson": "Funcții"}

def gen_s1_ex2(rng=random):
    return rng.choice(registry.get_generators(2))(rng)


# ─────────────────────────────── Slot 3 ───────────────────────────────

@registry.register(slot=3)
@template("s1_radical_equation", "Ecuații cu radicali", "medium")
def gen_s1_ex3_eq_radical(rng=random):
    c = rng.randint(2, 5)
    a = rng.choice([1, 2, 3])
    x = rng.randint(1, 6)
    b = c**2 - a*x
    text = f"Rezolvați în $\\mathbb{{R}}$ ecuația $\\sqrt{{{a}x {b:+}}} = {c}$."
    solution = (f"Condiție: ${a}x {b:+} \\geq 0 \\Rightarrow x \\geq {-b/a:.2f}$.\n"
                f"Ridicăm la pătrat: ${a}x {b:+} = {c**2} \\Rightarrow x = {x}$.\n"
                f"Verificăm: ${x} \\geq {-b/a:.2f}$ ✓. Soluție: $x = {x}$.")
    return {"id": "s1_ex3_eq_radical", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "x": x}, "lesson": "Radicali"}

@registry.register(slot=3)
@template("s1_exponential_equation", "Ecuații exponențiale", "medium")
def gen_s1_ex3_eq_exponential(rng=random):
    a = rng.choice([2, 3, 5])
    b = rng.choice([1, 2])
    x = rng.randint(1, 4)
    c = rng.randint(-3, 3)
    d = b*x + c
    rhs = a**d
    text = f"Rezolvați în $\\mathbb{{R}}$ ecuația ${a}^{{{b}x {c:+}}} = {rhs}$."
    solution = (f"${rhs} = {a}^{{{d}}}$. Deci ${a}^{{{b}x{c:+}}} = {a}^{{{d}}} \\Rightarrow {b}x{c:+} = {d} \\Rightarrow x = {x}$.")
    return {"id": "s1_ex3_eq_exponential", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "d": d, "rhs": rhs, "x": x}, "lesson": "Puteri"}

@registry.register(slot=3)
@template("s1_logarithmic_equation", "Ecuații logaritmice", "medium")
def gen_s1_ex3_eq_logarithmic(rng=random):
    base = rng.choice([2, 3, 5])
    d = rng.randint(1, 3)
    b = rng.choice([1, 2, 3])
    x = rng.randint(1, 5)
    c = base**d - b*x
    text = f"Rezolvați în $\\mathbb{{R}}$ ecuația $\\log_{{{base}}}({b}x {c:+}) = {d}$."
    solution = (f"Condiție: ${b}x {c:+} \\gt 0 \\Rightarrow x \\gt {-c/b:.2f}$.\n"
                f"${b}x {c:+} = {base}^{{{d}}} = {base**d} \\Rightarrow x = {x}$. Soluție: $x = {x}$.")
    return {"id": "s1_ex3_eq_logarithmic", "text": text, "solution": solution,
            "points": 5, "params": {"base": base, "b": b, "c": c, "d": d, "x": x}, "lesson": "Logaritmi"}

@registry.register(slot=3)
@template("s1_modular_equation", "Ecuații cu modul", "medium")
def gen_s1_ex3_eq_modular(rng=random):
    a = rng.randint(1, 4)
    b = rng.randint(2, 8)
    x1 = (b - a)
    x2 = -(b + a)
    text = f"Rezolvați în $\\mathbb{{R}}$ ecuația $|x {a:+}| = {b}$."
    solution = (f"$|x{a:+}| = {b}$ înseamnă $x{a:+} = {b}$ sau $x{a:+} = -{b}$.\n"
                f"$x_1 = {b} - {a} = {x1}$ sau $x_2 = -{b} - {a} = {x2}$.")
    return {"id": "s1_ex3_eq_modular", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "x1": x1, "x2": x2}, "lesson": "Funcții"}

@registry.register(slot=3)
@template("s1_quadratic_equation_discriminant", "Ecuații de gradul al doilea – discriminant", "easy")
def gen_s1_ex3_eq_quadratic(rng=random):
    x1 = rng.randint(-3, 0)
    x2 = rng.randint(1, 5)
    b = -(x1 + x2)
    c = x1 * x2
    discriminant = b**2 - 4*c
    text = f"Rezolvați în $\\mathbb{{R}}$ ecuația $x^2 {b:+}x {c:+} = 0$."
    solution = (f"$\\Delta = ({b})^2 - 4 \\cdot {c} = {discriminant}$.\n"
                f"$x_{{1,2}} = \\frac{{-({b}) \\pm \\sqrt{{{discriminant}}}}}{{2}}$. Soluții: $x_1 = {x1}$, $x_2 = {x2}$.")
    return {"id": "s1_ex3_eq_quadratic", "text": text, "solution": solution,
            "points": 5, "params": {"x1": x1, "x2": x2, "b": b, "c": c, "disc": discriminant}, "lesson": "Funcții"}

@registry.register(slot=3)
@template("s1_polynomial_remainder_theorem", "Teorema restului", "medium")
def gen_s1_ex3_poly_remainder(rng=random):
    a = rng.randint(1, 4)
    b = rng.randint(-5, 5)
    r = rng.choice([-3, -2, -1, 1, 2, 3])
    rem = r**3 - a*r + b
    text = f"Determinați restul împărțirii polinomului $P(X) = X^3 - {a}X {b:+}$ la $X {-r:+}$."
    solution = (f"Conform teoremei restului, restul împărțirii lui $P$ la $X-({r})$ este $P({r})$.\n"
                f"$P({r}) = {r}^3 - {a} \\cdot {r} {b:+} = {r**3} {-a*r:+} {b:+} = {rem}$.")
    return {"id": "s1_ex3_poly_remainder", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "r": r, "rem": rem}, "lesson": "Polinoame"}

@registry.register(slot=3)
@template("s1_polynomial_divisibility", "Divizibilitatea polinoamelor", "medium")
def gen_s1_ex3_poly_divisibility(rng=random):
    r = rng.choice([1, -1, 2, -2])
    m = rng.randint(1, 4)
    p1 = rng.randint(-3, 3)
    c = -(r**3 + m*r**2 + p1*r)
    text = (f"Determinați $c \\in \\mathbb{{R}}$ astfel încât polinomul "
            f"$P(X) = X^3 + {m}X^2 {p1:+}X {c:+}$ să fie divizibil cu $X {-r:+}$.")
    solution = (f"$P$ este divizibil cu $X-({r})$ $\\iff$ $P({r}) = 0$ (teorema restului).\n"
                f"$P({r}) = {r}^3 + {m} \\cdot {r}^2 {p1:+} \\cdot {r} + c = "
                f"{r**3 + m*r**2 + p1*r} + c = 0$.\n"
                f"Rezultă $c = {c}$.")
    return {"id": "s1_ex3_poly_divisibility", "text": text, "solution": solution,
            "points": 5, "params": {"r": r, "m": m, "p1": p1, "c": c}, "lesson": "Polinoame"}

@registry.register(slot=3)
@template("s1_poly_factorization", "Factorizarea polinoamelor", "medium")
def gen_s1_ex3_poly_factor(rng=random):
    r1 = rng.randint(-3, -1)
    r2 = rng.randint(1, 4)
    r3 = rng.choice([r1 - 1, r2 + 1, 0])
    # P(X) = (X - r1)(X - r2)(X - r3)
    # Expand to ax^3 + bx^2 + cx + d
    s  = r1 + r2 + r3
    p2 = r1*r2 + r1*r3 + r2*r3
    p3 = r1 * r2 * r3
    text = (f"Factorizați complet polinomul $P(X) = X^3 {-s:+}X^2 {p2:+}X {-p3:+}$, "
            f"știind că $x_1 = {r1}$ este o rădăcină.")
    solution = (f"Deoarece $x_1 = {r1}$ este rădăcină, $(X - ({r1}))$ divide $P(X)$.\n"
                f"Împărțind: $P(X) = (X {-r1:+})(X^2 + {-(r2+r3)}X {r2*r3:+})$.\n"
                f"Rădăcinile factorului pătratic: $x_2 = {r2}$, $x_3 = {r3}$.\n"
                f"$P(X) = (X {-r1:+})(X {-r2:+})(X {-r3:+})$.")
    return {"id": "s1_ex3_poly_factor", "text": text, "solution": solution,
            "points": 5, "params": {"r1": r1, "r2": r2, "r3": r3}, "lesson": "Polinoame"}

@registry.register(slot=3)
@template("s1_rational_expression_domain", "Domeniul și simplificarea fracțiilor algebrice", "medium")
def gen_s1_ex3_rational_expr(rng=random):
    a = rng.randint(1, 3)
    r = rng.randint(1, 4)
    # f(x) = (x^2 - r^2) / (x - r) = x + r, x ≠ r
    text = (f"Se consideră expresia $E(x) = \\dfrac{{x^2 - {r**2}}}{{x - {r}}}$.\n\n"
            f"a) Determinați domeniul de definiție al lui $E$.\n\n"
            f"b) Simplificați $E(x)$.\n\n"
            f"c) Calculați $E({r + 1})$.")
    solution = (f"a) $E$ este definită când $x - {r} \\neq 0$, deci $D = \\mathbb{{R}} \\setminus \\{{{r}\\}}$.\n\n"
                f"b) $x^2 - {r**2} = (x-{r})(x+{r})$, deci $E(x) = \\dfrac{{(x-{r})(x+{r})}}{{x-{r}}} = x + {r}$, "
                f"$x \\neq {r}$.\n\n"
                f"c) $E({r+1}) = {r+1} + {r} = {2*r+1}$.")
    return {"id": "s1_ex3_rational_expr", "text": text, "solution": solution,
            "points": 5, "params": {"r": r, "r2": r**2, "result": 2*r+1}, "lesson": "Polinoame"}

@registry.register(slot=3)
@template("s1_linear_system_substitution", "Sistem de ecuații liniare – substituție", "easy")
def gen_s1_ex3_linear_system(rng=random):
    x = rng.randint(1, 5)
    y = rng.randint(1, 5)
    a1, b1 = rng.randint(1, 3), rng.randint(1, 3)
    a2, b2 = rng.randint(1, 3), rng.randint(1, 3)
    while a1 * b2 == a2 * b1:  # ensure unique solution
        a2 = rng.randint(1, 3)
        b2 = rng.randint(1, 3)
    r1 = a1 * x + b1 * y
    r2 = a2 * x + b2 * y
    text = (f"Rezolvați sistemul $\\begin{{cases}} {a1}x + {b1}y = {r1} \\\\ {a2}x + {b2}y = {r2} \\end{{cases}}$.")
    solution = (f"Din prima ecuație: $x = \\dfrac{{{r1} - {b1}y}}{{{a1}}}$.\n"
                f"Înlocuind în a doua: se obține $y = {y}$, $x = {x}$.")
    return {"id": "s1_ex3_linear_system", "text": text, "solution": solution,
            "points": 5, "params": {"x": x, "y": y, "a1": a1, "b1": b1, "a2": a2, "b2": b2}, "lesson": "Funcții"}

@registry.register(slot=3)
@template("s1_log_properties", "Proprietățile logaritmilor", "medium")
def gen_s1_ex3_log_props(rng=random):
    base = rng.choice([2, 3, 10])
    a = rng.choice([2, 3, 4, 5, 6, 8, 9])
    b = rng.choice([2, 3, 4, 5])
    while a % b != 0 and b % a != 0 and a * b > 100:
        b = rng.choice([2, 3, 4, 5])
    prod = a * b
    quot = max(a, b) // min(a, b) if max(a, b) % min(a, b) == 0 else None
    n = rng.choice([2, 3])
    variants = [
        (
            f"$\\log_{{{base}}} {prod} = \\log_{{{base}}} {a} + \\log_{{{base}}} {b}$",
            f"$\\log_{{b}}(xy) = \\log_{{b}} x + \\log_{{b}} y$. Deci $\\log_{{{base}}} {prod} = \\log_{{{base}}} {a} + \\log_{{{base}}} {b}$ ✓",
            f"log_prod_{a}_{b}"
        ),
        (
            f"$\\log_{{{base}}} {a**n} = {n} \\log_{{{base}}} {a}$",
            f"$\\log_{{b}} x^n = n \\log_{{b}} x$. Deci $\\log_{{{base}}} {a}^{{{n}}} = {n} \\log_{{{base}}} {a}$ ✓",
            f"log_power_{a}_{n}"
        ),
    ]
    if quot is not None:
        large, small = max(a, b), min(a, b)
        variants.append((
            f"$\\log_{{{base}}} {large} - \\log_{{{base}}} {small} = \\log_{{{base}}} {quot}$",
            f"$\\log_{{b}}(x/y) = \\log_{{b}} x - \\log_{{b}} y$. Deci $\\log_{{{base}}} {large} - \\log_{{{base}}} {small} = \\log_{{{base}}} {quot}$ ✓",
            f"log_quot_{large}_{small}"
        ))
    eq_text, sol_text, pkey = rng.choice(variants)
    text = f"Verificați egalitatea {eq_text}."
    solution = sol_text
    return {"id": "s1_ex3_log_props", "text": text, "solution": solution,
            "points": 5, "params": {"variant": pkey, "base": base}, "lesson": "Logaritmi"}

@registry.register(slot=3)
@template("s1_poly_multiplication", "Multiplicarea polinoamelor", "easy")
def gen_s1_ex3_poly_mult(rng=random):
    a = rng.randint(1, 4)
    b = rng.randint(1, 5)
    c = rng.randint(1, 4)
    d = rng.randint(1, 5)
    # (ax + b)(cx + d) = acx^2 + (ad+bc)x + bd
    ac = a * c
    ad_bc = a * d + b * c
    bd = b * d
    text = (f"Calculati produsul $(${a}x {b:+})(${c}x {d:+})$ și scriel sub forma "
            f"$Ax^2 + Bx + C$.")
    # fix text
    text = (f"Calculați produsul $({a}x {b:+})({c}x {d:+})$.")
    solution = (f"$({a}x {b:+})({c}x {d:+}) = "
                f"{a}x \\cdot {c}x + {a}x \\cdot ({d:+}) + ({b:+}) \\cdot {c}x + ({b:+})({d:+})$\n"
                f"$= {ac}x^2 {a*d:+}x {b*c:+}x {bd:+} = {ac}x^2 {ad_bc:+}x {bd:+}$.")
    return {"id": "s1_ex3_poly_mult", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "d": d, "ac": ac, "ad_bc": ad_bc, "bd": bd}, "lesson": "Polinoame"}

def gen_s1_ex3(rng=random):
    return rng.choice(registry.get_generators(3))(rng)


# ─────────────────────────────── Slot 4 ───────────────────────────────

@registry.register(slot=4)
@template("s1_classical_probability", "Probabilitate clasică", "easy")
def gen_s1_ex4_prob(rng=random):
    k = rng.randint(7, 15)
    multiples = [i for i in range(10, 100) if i % k == 0]
    fav = len(multiples)
    total = 90
    g = math.gcd(fav, total)
    text = (f"Calculați probabilitatea ca un număr de două cifre ales aleatoriu "
            f"să fie divizibil cu ${k}$.")
    solution = (f"Total cazuri: $90$. Favorabile: {', '.join(map(str,multiples))} → ${fav}$ cazuri.\n"
                f"$P = \\frac{{{fav}}}{{{total}}} = \\frac{{{fav//g}}}{{{total//g}}}$.")
    return {"id": "s1_ex4_prob", "text": text, "solution": solution,
            "points": 5, "params": {"k": k, "fav": fav, "total": total}, "lesson": "Probabilități"}

@registry.register(slot=4)
@template("s1_combinatorics_CnA", "Combinări și aranjamente", "medium")
def gen_s1_ex4_comb(rng=random):
    n = rng.randint(4, 6)
    m = rng.randint(3, 4)
    cnk = math.comb(n, 2)
    amp = math.perm(m, 2)
    val = cnk - amp
    text = f"Calculați $C_{{{n}}}^{{2}} - A_{{{m}}}^{{2}}$."
    solution = (f"$C_{{{n}}}^{{2}} = \\frac{{{n} \\cdot {n-1}}}{{2}} = {cnk}$;\n"
                f"$A_{{{m}}}^{{2}} = {m} \\cdot {m-1} = {amp}$.\n"
                f"Rezultat: ${cnk} - {amp} = {val}$.")
    return {"id": "s1_ex4_comb", "text": text, "solution": solution,
            "points": 5, "params": {"n": n, "m": m, "cnk": cnk, "amp": amp, "val": val}, "lesson": "Probabilități"}

@registry.register(slot=4)
@template("s1_percentage_price", "Aplicații cu procente – prețuri", "easy")
def gen_s1_ex4_finance(rng=random):
    P = rng.choice([100, 200, 300, 500, 1000])
    p = rng.choice([10, 15, 20, 25])
    increase = int(P * p / 100)
    text = (f"După o scumpire cu ${p}\\%$, prețul unui produs crește cu ${increase}$ lei. "
            f"Determinați prețul inițial.")
    solution = (f"$\\frac{{{p}}}{{100}} \\cdot x = {increase} \\Rightarrow x = {P}$ lei.")
    return {"id": "s1_ex4_finance", "text": text, "solution": solution,
            "points": 5, "params": {"P": P, "p": p, "increase": increase}, "lesson": "Progresii"}

@registry.register(slot=4)
@template("s1_geometric_probability", "Probabilitate geometrică", "medium")
def gen_s1_ex4_geom_prob(rng=random):
    n = rng.choice([4, 5, 6])
    k = rng.randint(1, n-1)
    p_num = k
    p_den = n
    g = math.gcd(p_num, p_den)
    text = (f"Un segment de lungime ${n}$ cm conține un punct ales aleatoriu. "
            f"Calculați probabilitatea ca punctul să fie în primii ${k}$ cm.")
    solution = (f"$P = \\frac{{{k}}}{{{n}}} = \\frac{{{k//g}}}{{{n//g}}}$.")
    return {"id": "s1_ex4_geom_prob", "text": text, "solution": solution,
            "points": 5, "params": {"n": n, "k": k}, "lesson": "Probabilități"}

@registry.register(slot=4)
@template("s1_mixed_events_probability", "Probabilitatea reuniunii evenimentelor", "medium")
def gen_s1_ex4_prob_union(rng=random):
    p_a = rng.choice([1, 2, 3])
    p_b = rng.choice([1, 2, 3])
    denom = 10
    p_ab = 1
    p_union_num = p_a + p_b - p_ab
    text = (f"Probabilitățile a două evenimente independente sunt $P(A) = \\frac{{{p_a}}}{{{denom}}}$ "
            f"și $P(B) = \\frac{{{p_b}}}{{{denom}}}$. Calculați $P(A \\cup B)$ știind că "
            f"$P(A \\cap B) = \\frac{{1}}{{{denom}}}$.")
    solution = (f"$P(A \\cup B) = P(A) + P(B) - P(A \\cap B) = "
                f"\\frac{{{p_a}}}{{{denom}}} + \\frac{{{p_b}}}{{{denom}}} - \\frac{{1}}{{{denom}}} = "
                f"\\frac{{{p_union_num}}}{{{denom}}}$.")
    return {"id": "s1_ex4_prob_union", "text": text, "solution": solution,
            "points": 5, "params": {"p_a": p_a, "p_b": p_b, "denom": denom, "p_union_num": p_union_num}, "lesson": "Probabilități"}

@registry.register(slot=4)
@template("s1_binomial_theorem", "Teorema binomului – coeficienți", "medium")
def gen_s1_ex4_binomial(rng=random):
    n = rng.choice([4, 5, 6])
    k = rng.randint(1, n - 1)
    a = rng.choice([1, 2])
    b = rng.choice([1, 2, 3])
    coeff = math.comb(n, k) * (a ** (n - k)) * (b ** k)
    text = (f"Determinați coeficientul lui $x^{{{k}}}$ în dezvoltarea binomului "
            f"$({a} + {b}x)^{{{n}}}$.")
    solution = (f"Termenul general al dezvoltării: $T_{{k+1}} = C_{{{n}}}^{{k}} \\cdot {a}^{{{n}-k}} \\cdot ({b}x)^k$.\n"
                f"Pentru $x^{{{k}}}$: $k = {k}$.\n"
                f"$T_{{{k+1}}} = C_{{{n}}}^{{{k}}} \\cdot {a}^{{{n-k}}} \\cdot {b}^{{{k}}} \\cdot x^{{{k}}} "
                f"= {math.comb(n,k)} \\cdot {a**(n-k)} \\cdot {b**k} \\cdot x^{{{k}}} = {coeff}x^{{{k}}}$.")
    return {"id": "s1_ex4_binomial", "text": text, "solution": solution,
            "points": 5, "params": {"n": n, "k": k, "a": a, "b": b, "coeff": coeff}, "lesson": "Probabilități"}

@registry.register(slot=4)
@template("s1_permutations_word", "Permutări – aranjarea obiectelor", "easy")
def gen_s1_ex4_permutations(rng=random):
    n = rng.randint(3, 6)
    pn = math.factorial(n)
    r = rng.randint(2, min(n, 3))
    pr = math.perm(n, r)
    text = (f"a) Calculați $P_{{{n}}} = {n}!$.\n\n"
            f"b) Calculați $A_{{{n}}}^{{{r}}}$.")
    solution = (f"a) $P_{{{n}}} = {n}! = {pn}$.\n\n"
                f"b) $A_{{{n}}}^{{{r}}} = {n} \\cdot {n-1} \\cdots {n-r+1} = {pr}$.")
    return {"id": "s1_ex4_permutations", "text": text, "solution": solution,
            "points": 5, "params": {"n": n, "pn": pn, "r": r, "pr": pr}, "lesson": "Probabilități"}

def gen_s1_ex4(rng=random):
    return rng.choice(registry.get_generators(4))(rng)
