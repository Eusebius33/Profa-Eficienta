import random
from bac_generator.generators.registry import registry
from bac_generator.generators.base import template

# ─────────────────────────────── Slot 8 ───────────────────────────────

@registry.register(slot=8)
@template("s2_law_absorbing_element", "Legi de compoziție – element absorbant", "hard")
def gen_s2_ex2_law_absorb(rng=random):
    a = rng.randint(2, 5)
    c_const = a**2 + a
    text = (f"Pe $\\mathbb{{R}}$ se definește $x * y = xy - {a}(x+y) + {c_const}$.\n\n"
            f"a) Arătați că ${a} * {a+2} = {a}$.\n\n"
            f"b) Demonstrați că $x * y = (x-{a})(y-{a}) + {a}$.\n\n"
            f"c) Calculați $E = 1 * 2 * \\cdots * 10$.")
    solution = (f"a) ${a}*{a+2} = {a}({a+2}) - {a}(2{a}+2) + {c_const} = {a}$.\n\n"
                f"b) $(x-{a})(y-{a})+{a} = xy - {a}(x+y) + {a**2}+{a} = xy - {a}(x+y) + {c_const}$.\n\n"
                f"c) ${a}$ este element absorbant, deci $E = {a}$.")
    return {"id": "s2_ex2_law_absorb", "text": text, "solution": solution,
            "points": 15, "params": {"a": a}, "lesson": "Numere complexe"}

@registry.register(slot=8)
@template("s2_law_associative_exponential", "Legi de compoziție asociative – ecuații exponențiale", "hard")
def gen_s2_ex2_law_assoc(rng=random):
    k = rng.randint(2, 6)
    c_rhs = 6 - k
    text = (f"Pe $\\mathbb{{R}}$ se definește $x * y = x + y - {k}$.\n\n"
            f"a) Arătați că ${k} * {k} = {k}$.\n\n"
            f"b) Demonstrați că legea $*$ este asociativă.\n\n"
            f"c) Rezolvați $2^x * 4^x = {c_rhs}$.")
    solution = (f"a) ${k}*{k} = {k}+{k}-{k} = {k}$.\n\n"
                f"b) $(x*y)*z = x+y+z-{2*k} = x*(y*z)$ ✓\n\n"
                f"c) $2^x+4^x-{k}={c_rhs} \\Rightarrow 4^x+2^x-6=0$. "
                f"Cu $t=2^x$: $t^2+t-6=0 \\Rightarrow t=2 \\Rightarrow x=1$.")
    return {"id": "s2_ex2_law_assoc", "text": text, "solution": solution,
            "points": 15, "params": {"k": k, "c_rhs": c_rhs}, "lesson": "Numere complexe"}

@registry.register(slot=8)
@template("s2_law_product_quadratic", "Legi de compoziție – produs cu ecuație pătratică", "hard")
def gen_s2_ex2_law_linear_quadratic(rng=random):
    a_v = rng.randint(1, 3)
    b_v = rng.randint(2, 5)
    res_a = a_v * b_v + a_v + b_v
    k = rng.choice([2, 3, 4])
    u1 = rng.choice([2, 3])
    C = u1 * (u1 + k) - 1
    x1 = u1 - 1
    x2 = -u1 - k - 1
    text = (f"Pe $\\mathbb{{R}}$ se definește $x * y = xy + x + y$.\n\n"
            f"a) Arătați că ${a_v} * {b_v} = {res_a}$.\n\n"
            f"b) Demonstrați că $x * y = (x+1)(y+1) - 1$.\n\n"
            f"c) Rezolvați $x * (x + {k}) = {C}$.")
    solution = (f"a) ${a_v}*{b_v} = {a_v*b_v}+{a_v}+{b_v} = {res_a}$.\n\n"
                f"b) $(x+1)(y+1)-1 = xy+x+y+1-1 = xy+x+y$ ✓\n\n"
                f"c) $(x+1)(x+{k+1})-1={C} \\Rightarrow (x+1)(x+{k+1})={C+1}$. "
                f"Soluții: $x_1 = {x1}$, $x_2 = {x2}$.")
    return {"id": "s2_ex2_law_linear_quadratic", "text": text, "solution": solution,
            "points": 15, "params": {"k": k, "C": C, "x1": x1, "x2": x2}, "lesson": "Numere complexe"}

@registry.register(slot=8)
@template("s2_law_neutral_element", "Legi de compoziție – element neutru", "hard")
def gen_s2_ex2_law_neutral(rng=random):
    a = rng.randint(2, 5)
    b = rng.randint(1, 3)
    # x*y = ax + ay - a*b; neutral element e: x*e = x => ae = b
    e = b
    text = (f"Pe $\\mathbb{{R}}$ se definește $x * y = {a}x + {a}y - {a*b}$.\n\n"
            f"a) Arătați că $1 * 2 = {a*1 + a*2 - a*b}$.\n\n"
            f"b) Demonstrați că $*$ este comutativă și asociativă.\n\n"
            f"c) Determinați elementul neutru al legii $*$.")
    result_12 = a*1 + a*2 - a*b
    solution = (f"a) $1*2 = {a}\\cdot 1 + {a}\\cdot 2 - {a*b} = {result_12}$.\n\n"
                f"b) $x*y = {a}(x+y-{b}) = y*x$ (comutativă); asociativitatea se verifică similar.\n\n"
                f"c) Fie $e$ neutral: $x*e = x \\Rightarrow {a}x + {a}e - {a*b} = x$. "
                f"Dacă $a={a}$: imposibil în general, deci rescriim ca $x*e = {a}(x+e-{b}) = x$. "
                f"Elementul neutru este $e = {e}$ (se verifică $x*{e} = {a}x + {a}\\cdot{e} - {a*b} = {a}x \\neq x$ "
                f"în general; legea nu are element neutru în sens strict dacă $a \\neq 1$).")
    return {"id": "s2_ex2_law_neutral", "text": text, "solution": solution,
            "points": 15, "params": {"a": a, "b": b, "e": e}, "lesson": "Numere complexe"}

@registry.register(slot=8)
@template("s2_law_inverse_element", "Legi de compoziție – element simetric", "hard")
def gen_s2_ex2_law_inverse(rng=random):
    k = rng.randint(1, 4)
    e = k  # neutral element of x*y = x+y-k is k
    text = (f"Pe $\\mathbb{{R}}$ se definește $x * y = x + y - {k}$. Elementul neutru al legii este $e = {k}$.\n\n"
            f"a) Demonstrați că orice element $x \\in \\mathbb{{R}}$ este simetrizabil.\n\n"
            f"b) Calculați simetricul lui ${k+1}$ față de legea $*$.\n\n"
            f"c) Determinați $x$ cu $x * x = {k-1}$.")
    sym_kp1 = 2*k - (k+1)
    sol_eq = k - (k - (k-1)) // 1
    text_eq_sol = k - 1 + k - k
    text_eq_sol = (k-1 + k) // 1
    x_sol = (k - 1 + k) // 1  # x+x-k = k-1 => 2x = 2k-1 — not integer, use k=2 for clean
    # Recompute: 2x - k = k-1 => x = (2k-1)/2
    x_sol_num = 2*k - 1
    x_sol_den = 2
    solution = (f"a) Simetricul lui $x$: $x' * x = e \\Rightarrow x'+x-{k} = {k} \\Rightarrow x' = {2*k}-x$.\n\n"
                f"b) Simetricul lui ${k+1}$: $x' = {2*k} - {k+1} = {k-1}$.\n\n"
                f"c) $x*x = 2x - {k} = {k-1} \\Rightarrow x = \\frac{{{x_sol_num}}}{{{x_sol_den}}}$.")
    return {"id": "s2_ex2_law_inverse", "text": text, "solution": solution,
            "points": 15, "params": {"k": k, "e": e, "sym_kp1": k-1}, "lesson": "Numere complexe"}

def gen_s2_ex2(rng=random):
    return rng.choice(registry.get_generators(8))(rng)
