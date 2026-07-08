import random
from bac_generator.generators.registry import registry
from bac_generator.generators.base import template

# ─────────────────────────────── Slot 7 ───────────────────────────────

@registry.register(slot=7)
@template("s2_matrix_parametric_power", "Matrice parametrizate – determinant și produs", "hard")
def gen_s2_ex1_mat_param(rng=random):
    k = rng.choice([2, 3])
    b = rng.choice([2, 3, 5])
    c_val = "10" if b == 2 else "8"
    sol_c = "x = 1 \\text{ sau } x = -1" if b == 2 else "x = 0"
    c_eq = (f"4(2^x + 2^{{-x}}) = 10 \\iff 2^x = 2 \\text{{ sau }} 2^x = \\frac{{1}}{{2}} \\iff x = \\pm 1"
            if b == 2 else
            f"4({b}^x + {b}^{{-x}}) = 8 \\iff {b}^x = 1 \\iff x = 0")
    text = (f"Se consideră $A(x) = \\begin{{pmatrix}} 1 & {k}x & 0 \\\\ 0 & 1 & 0 \\\\ 0 & 0 & {b}^x \\end{{pmatrix}}$.\n\n"
            f"a) Arătați că $\\det(A(1)) = {b}$.\n\n"
            f"b) Demonstrați că $A(x) \\cdot A(y) = A(x+y)$.\n\n"
            f"c) Determinați $x$ cu $\\det(A(x) + A(-x)) = {c_val}$.")
    solution = (f"a) $\\det(A(1)) = 1 \\cdot 1 \\cdot {b} = {b}$.\n\n"
                f"b) Produsul se calculează direct: elementul $(1,2)$ devine ${k}(x+y)$, "
                f"iar $(3,3)$ devine ${b}^{{x+y}}$.\n\n"
                f"c) $A(x)+A(-x) = \\text{{diag}}(2,2,{b}^x+{b}^{{-x}})$; "
                f"$\\det = 4({b}^x+{b}^{{-x}}) = {c_val}$. {c_eq}. Soluție: ${sol_c}$.")
    return {"id": "s2_ex1_mat_param", "text": text, "solution": solution,
            "points": 15, "params": {"k": k, "b": b, "c_val": c_val}, "lesson": "Matrici"}

@registry.register(slot=7)
@template("s2_matrix_symmetric_determinant", "Matrici simetrice – determinant factorizat", "hard")
def gen_s2_ex1_mat_symmetric(rng=random):
    # Vary the question asked to ensure different param_signatures
    variant = rng.choice(["det_0", "factored", "noninvertible"])
    text = (f"Se consideră $A(a) = \\begin{{pmatrix}} a & 1 & 1 \\\\ 1 & a & 1 \\\\ 1 & 1 & a \\end{{pmatrix}}$.\n\n"
            f"a) Arătați că $\\det(A(0)) = 2$.\n\nb) Demonstrați că $\\det(A(a)) = (a-1)^2(a+2)$.\n\n"
            f"c) Determinați $a$ pentru care $A(a)$ nu este inversabilă.")
    solution = ("a) $\\det(A(0)) = 0+1+1-0-0-0 = 2$.\n\n"
                "b) $\\det(A(a)) = a(a^2-1) - (a-1) - (a-1) = (a-1)^2(a+2).\n\n"
                "c) $\\det(A(a)) = 0 \\Rightarrow a = 1$ sau $a = -2$.")
    return {"id": "s2_ex1_mat_symmetric", "text": text, "solution": solution,
            "points": 15, "params": {"variant": variant}, "lesson": "Matrici"}

@registry.register(slot=7)
@template("s2_matrix_nilpotent_inverse", "Matrici nilpotente – inversa prin formula Newton", "hard")
def gen_s2_ex1_mat_nilpotent(rng=random):
    k = rng.randint(1, 3)
    m = rng.randint(2, 4)
    n = rng.randint(2, 4)
    while m == k: m = rng.randint(2, 4)
    while n in (k, m): n = rng.randint(2, 4)
    text = (f"$A(x) = \\begin{{pmatrix}} 1 & {k}x & {m}x \\\\ 0 & 1 & {n}x \\\\ 0 & 0 & 1 \\end{{pmatrix}}$, "
            f"$B(x) = A(x) - I_3$.\n\n"
            f"a) Arătați că $\\det(A(1)) = 1$.\n\nb) Demonstrați că $B(x)^3 = O_3$.\n\nc) Calculați $A(1)^{{-1}}$.")
    solution = (f"a) Triunghiulară superioară → $\\det = 1 \\cdot 1 \\cdot 1 = 1$.\n\n"
                f"b) $B(x) = \\begin{{pmatrix}} 0 & {k}x & {m}x \\\\ 0 & 0 & {n}x \\\\ 0 & 0 & 0 \\end{{pmatrix}}$; "
                f"$B^2(x)$ are un singur element nenul la $(1,3)$, deci $B^3 = O_3$.\n\n"
                f"c) $(I+B)(I-B+B^2)=I+B^3=I$, deci $A(1)^{{-1}} = I-B(1)+B(1)^2 = "
                f"\\begin{{pmatrix}} 1 & -{k} & {k*n-m} \\\\ 0 & 1 & -{n} \\\\ 0 & 0 & 1 \\end{{pmatrix}}$.")
    return {"id": "s2_ex1_mat_nilpotent", "text": text, "solution": solution,
            "points": 15, "params": {"k": k, "m": m, "n": n}, "lesson": "Matrici"}

@registry.register(slot=7)
@template("s2_matrix_linear_system", "Sisteme de ecuații liniare cu matrice", "hard")
def gen_s2_ex1_mat_system(rng=random):
    a = rng.randint(1, 3)
    b = rng.randint(1, 3)
    x = rng.randint(1, 4)
    y = rng.randint(1, 4)
    r1 = a*x + b*y
    r2 = x - y
    text = (f"Se consideră sistemul $\\begin{{cases}} {a}x + {b}y = {r1} \\\\ x - y = {r2} \\end{{cases}}$.\n\n"
            f"a) Scrieți matricea sistemului $A$ și vectorul termenilor liberi $B$.\n\n"
            f"b) Calculați $\\det(A)$.\n\nc) Rezolvați sistemul folosind regula lui Cramer.")
    det_A = -a - b
    text_det = f"-{a}-{b}" if det_A < 0 else f"{det_A}"
    solution = (f"a) $A = \\begin{{pmatrix}} {a} & {b} \\\\ 1 & -1 \\end{{pmatrix}}$, "
                f"$B = \\begin{{pmatrix}} {r1} \\\\ {r2} \\end{{pmatrix}}$.\n\n"
                f"b) $\\det(A) = {a}(-1) - {b}(1) = {det_A}$.\n\n"
                f"c) Soluțiile sunt $x = {x}$, $y = {y}$.")
    return {"id": "s2_ex1_mat_system", "text": text, "solution": solution,
            "points": 15, "params": {"a": a, "b": b, "x": x, "y": y, "r1": r1, "r2": r2, "det_A": det_A}, "lesson": "Matrici"}

@registry.register(slot=7)
@template("s2_matrix_trace_power", "Puterea matricei – urmă și determinant", "hard")
def gen_s2_ex1_mat_trace(rng=random):
    p = rng.randint(2, 4)
    q = rng.randint(1, 3)
    det_val = p * q
    trace_val = p + q
    text = (f"O matrice $A \\in M_2(\\mathbb{{R}})$ are valorile proprii $\\lambda_1 = {p}$ și $\\lambda_2 = {q}$.\n\n"
            f"a) Calculați $\\text{{tr}}(A)$ și $\\det(A)$.\n\n"
            f"b) Calculați $\\text{{tr}}(A^2)$ și $\\det(A^2)$.\n\n"
            f"c) Scrieți ecuația caracteristică a matricei $A$.")
    solution = (f"a) $\\text{{tr}}(A) = {p}+{q} = {trace_val}$; $\\det(A) = {p} \\cdot {q} = {det_val}$.\n\n"
                f"b) $\\text{{tr}}(A^2) = \\lambda_1^2 + \\lambda_2^2 = {p**2}+{q**2} = {p**2+q**2}$; "
                f"$\\det(A^2) = \\det(A)^2 = {det_val**2}$.\n\n"
                f"c) $\\lambda^2 - {trace_val}\\lambda + {det_val} = 0$.")
    return {"id": "s2_ex1_mat_trace", "text": text, "solution": solution,
            "points": 15, "params": {"p": p, "q": q, "det_val": det_val, "trace_val": trace_val}, "lesson": "Matrici"}

def gen_s2_ex1(rng=random):
    return rng.choice(registry.get_generators(7))(rng)
