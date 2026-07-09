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

@registry.register(slot=1)
@template("s1_log_properties", "Proprietăți ale logaritmilor", "easy")
def gen_s1_log_properties(rng=random):
    base = rng.choice([2, 3])
    a = rng.randint(1, 3)
    b = rng.randint(1, 3)
    val = a + b
    val_a = base**a
    val_b = base**b
    text = f"Calculați $E = \\log_{{{base}}}{{{val_a}}} + \\log_{{{base}}}{{{val_b}}} - \\log_{{{base}}}{{{base}^{{val-1}}}}$."
    solution = (f"$\\log_a(x) + \\log_a(y) = \\log_a(xy)$:\n"
                f"$E = \\log_{{{base}}}({val_a} \\cdot {val_b}) - \\log_{{{base}}}{{{base}^{{val-1}}}} = "
                f"\\log_{{{base}}}({base}^{{{val}}}) - ({val-1}) = {val} - {val-1} = 1$.")
    return {"id": "s1_log_properties", "text": text, "solution": solution,
            "points": 5, "params": {"base": base, "a": a, "b": b}, "lesson": "Logaritmi"}

@registry.register(slot=1)
@template("s1_induction_sum", "Inducție matematică", "medium")
def gen_s1_induction(rng=random):
    n = rng.choice([3, 4])
    sum_val = n * (n + 1) // 2
    text = f"Folosind inducția matematică, arătați că $1 + 2 + \\dots + n = \\frac{{n(n+1)}}{{2}}$ este adevărată pentru $n = {n}$."
    solution = (f"Pentru $n = {n}$: membru stâng: $1 + 2 + \\dots + {n} = {sum_val}$.\n"
                f"Membru drept: $\\frac{{{n}({n}+1)}}{{2}} = \\frac{{{n} \\cdot ({n}+1)}}{{2}} = {sum_val}$."
                f"Egalitatea este adevărată pentru $n = {n}$.")
    return {"id": "s1_induction", "text": text, "solution": solution,
            "points": 5, "params": {"n": n, "sum_val": sum_val}, "lesson": "Progresii"}

@registry.register(slot=1)
@template("s1_complex_operations", "Operații cu numere complexe", "easy")
def gen_s1_complex_operations(rng=random):
    a = rng.randint(1, 4)
    val = a**2 - 1
    text = f"Calculați partea reală a numărului complex $z = ({a} + i)^2 - {2*a}i$."
    solution = (f"$({a}+i)^2 = {a**2} + {2*a}i - 1 = {a**2-1} + {2*a}i$.\n"
                f"Atunci $z = {a**2-1} + {2*a}i - {2*a}i = {val}$."
                f"Partea reală este $\\text{{Re}}(z) = {val}$.")
    return {"id": "s1_complex_operations", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "val": val}, "lesson": "Numere complexe"}

@registry.register(slot=2)
@template("s1_func_domain_range", "Domeniu și codomeniu de funcție", "easy")
def gen_s1_ex2_domain_range(rng=random):
    a = rng.randint(2, 6)
    text = f"Determinați domeniul maxim de definiție $D \\subset \\mathbb{{R}}$ al funcției $f(x) = \\sqrt{{{a} - x}}$."
    solution = (f"Pentru ca radicalul să existe, expresia de sub radical trebuie să fie nenegativă:\n"
                f"${a} - x \\geq 0 \\Rightarrow x \\leq {a}$.\n"
                f"Domeniul maxim este $D = (-\\infty, {a}].$")
    return {"id": "s1_func_domain_range", "text": text, "solution": solution,
            "points": 5, "params": {"a": a}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_func_composition_inverse", "Compunerea și inversa unei funcții liniare", "medium")
def gen_s1_ex2_composition_inverse(rng=random):
    a = rng.randint(2, 4)
    b = rng.randint(1, 3)
    val_x = 1
    val_y = a**2 * 1 + a*b + b
    text = (f"Se consideră funcția $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = {a}x + {b}$.\n\n"
            f"Determinați $x \\in \\mathbb{{R}}$ pentru care $(f \\circ f)(x) = {val_y}$.")
    solution = (f"$(f \\circ f)(x) = f(f(x)) = {a}({a}x + {b}) + {b} = {a**2}x + {a*b+b}$.\n"
                f"Ecuația devine ${a**2}x + {a*b+b} = {val_y} \\Rightarrow {a**2}x = {a**2} \\Rightarrow x = {val_x}$.")
    return {"id": "s1_func_composition_inverse", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "val_x": val_x, "val_y": val_y}, "lesson": "Funcții"}

@registry.register(slot=2)
@template("s1_graph_reading", "Interpretarea graficului unei funcții", "easy")
def gen_s1_ex2_graph_reading(rng=random):
    a = rng.randint(1, 4)
    text = f"Graficul unei funcții $f(x) = ax + b$ trece prin $A(0, {a})$ și $B(1, {a+2})$. Determinați $a$ și $b$."
    solution = (f"$f(0) = b \\Rightarrow b = {a}$.\n"
                f"$f(1) = a + b = a + {a} = {a+2} \\Rightarrow a = 2$.\n"
                f"Deci $a = 2$ și $b = {a}$.")
    return {"id": "s1_graph_reading", "text": text, "solution": solution,
            "points": 5, "params": {"a": a}, "lesson": "Funcții"}

@registry.register(slot=3)
@template("s1_linear_equation", "Ecuații liniare", "easy")
def gen_s1_ex3_linear_eq(rng=random):
    a = rng.randint(2, 6)
    b = rng.randint(1, 10)
    x = rng.randint(1, 5)
    c = a * x + b
    text = f"Rezolvați în $\\mathbb{{R}}$ ecuația ${a}x {b:+} = {c}$."
    solution = f"${a}x = {c} {-b:+} \\Rightarrow {a}x = {c-b} \\Rightarrow x = {x}$."
    return {"id": "s1_linear_equation", "text": text, "solution": solution,
            "points": 5, "params": {"a": a, "b": b, "c": c, "x": x}, "lesson": "Funcții"}

@registry.register(slot=3)
@template("s1_poly_operations", "Operații cu polinoame și factorizare", "medium")
def gen_s1_ex3_poly_operations(rng=random):
    a = rng.randint(1, 3)
    text = f"Se consideră polinomul $P(X) = X^3 - {a}X^2 - X + {a}$. Factorizați polinomul în $\\mathbb{{R}}[X]$."
    solution = (f"Grupăm termenii: $P(X) = X^2(X - {a}) - (X - {a}) = (X - {a})(X^2 - 1)$.\n"
                f"Deoarece $X^2-1 = (X-1)(X+1)$:\n"
                f"$P(X) = (X - {a})(X - 1)(X + 1)$.")
    return {"id": "s1_poly_operations", "text": text, "solution": solution,
            "points": 5, "params": {"a": a}, "lesson": "Polinoame"}

@registry.register(slot=3)
@template("s1_rational_expressions", "Simplificarea fracțiilor algebrice", "medium")
def gen_s1_ex3_rational_expressions(rng=random):
    a = rng.randint(1, 4)
    text = f"Simplificați expresia fracției algebrice $E(x) = \\frac{{x^2 - {a**2}}}{{x^2 - {a}x}}$ pentru $x \\notin \\{{0, {a}\\}}$."
    solution = (f"Factorizăm numărătorul: $x^2 - {a**2} = (x-{a})(x+{a})$.\n"
                f"Factorizăm numitorul: $x^2 - {a}x = x(x-{a})$.\n"
                f"Simplificând cu $x-{a}$ obținem: $E(x) = \\frac{{x+{a}}}{{x}}$." )
    return {"id": "s1_rational_expressions", "text": text, "solution": solution,
            "points": 5, "params": {"a": a}, "lesson": "Radicali"}

@registry.register(slot=4)
@template("s1_permutations", "Permutări", "easy")
def gen_s1_ex4_permutations(rng=random):
    n = rng.randint(3, 5)
    p_val = math.factorial(n)
    text = f"Calculați numărul de permutări de ${n}$ elemente, adică $P_{{{n}}}$."
    solution = f"$P_{{{n}}} = {n}! = " + " \\cdot ".join(map(str, range(1, n+1))) + f" = {p_val}$."
    return {"id": "s1_permutations", "text": text, "solution": solution,
            "points": 5, "params": {"n": n, "p_val": p_val}, "lesson": "Probabilități"}

@registry.register(slot=4)
@template("s1_binomial_term", "Termenul general din dezvoltarea binomială", "medium")
def gen_s1_ex4_binomial(rng=random):
    n = rng.randint(4, 6)
    cn2 = math.comb(n, 2)
    text = f"Determinați coeficientul termenului $T_3$ al dezvoltării $(x + 1)^{{{n}}}$."
    solution = (f"Formula termenului general este $T_{{k+1}} = C_n^k a^{{n-k}} b^k$.\n"
                f"Pentru $T_3$, avem $k=2$. Atunci $T_3 = C_{{{n}}}^{{2}} x^{{{n-2}}} 1^2$.\n"
                f"Coeficientul lui $T_3$ este $C_{{{n}}}^{{2}} = {cn2}$.")
    return {"id": "s1_binomial", "text": text, "solution": solution,
            "points": 5, "params": {"n": n, "cn2": cn2}, "lesson": "Probabilități"}

@registry.register(slot=4)
@template("s1_mixed_applications", "Probleme aplicative de numărare", "medium")
def gen_s1_ex4_mixed_applications(rng=random):
    price = rng.choice([100, 200, 300, 500])
    p = rng.choice([10, 20])
    discount = price * p // 100
    final_price = price - discount
    text = f"Un produs costă {price} lei. Determinați prețul final al produsului după o reducere de {p}\\%."
    solution = (f"Reducerea este $\\frac{{{p}}}{{100}} \\cdot {price} = {discount}$ lei.\n"
                f"Prețul final este ${price} - {discount} = {final_price}$ lei.")
    return {"id": "s1_mixed_applications", "text": text, "solution": solution,
            "points": 5, "params": {"price": price, "p": p, "final_price": final_price}, "lesson": "Progresii"}

def gen_s1_ex4(rng=random):
    return rng.choice(registry.get_generators(4))(rng)
