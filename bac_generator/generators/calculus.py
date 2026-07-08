import random
from bac_generator.generators.registry import registry
from bac_generator.generators.base import template

# ─────────────────────────────── Slot 9 ───────────────────────────────

@registry.register(slot=9)
@template("s3_derivative_log_product", "Derivata produsului – funcții logaritmice", "hard")
def gen_s3_ex1_deriv_log(rng=random):
    a = rng.randint(1, 4)
    text = (f"Se consideră $f: (0, \\infty) \\to \\mathbb{{R}}$, $f(x) = x \\ln x - {a}x$.\n\n"
            f"a) Arătați că $f'(x) = \\ln x + 1 - {a}$.\n\n"
            f"b) Determinați ecuația tangentei la graficul funcției în $x_0 = 1$.\n\n"
            f"c) Demonstrați că $f(x) \\geq -e^{{{a-1}}}$ pentru orice $x \\in (0, \\infty)$.")
    solution = (f"a) $f'(x) = \\ln x + x \\cdot \\frac{{1}}{{x}} - {a} = \\ln x + 1 - {a}$.\n\n"
                f"b) $f(1) = -{a}$, $f'(1) = {1-a}$. Tangenta: $y = {1-a}x - 1$.\n\n"
                f"c) $f'(x) = 0 \\Rightarrow x = e^{{{a-1}}}$ (minim). "
                f"$f(e^{{{a-1}}}) = e^{{{a-1}}}({a-1}-{a}) = -e^{{{a-1}}}$.")
    return {"id": "s3_ex1_deriv_log", "text": text, "solution": solution,
            "points": 15, "params": {"a": a}, "lesson": "Derivate"}

@registry.register(slot=9)
@template("s3_derivative_exponential_product", "Derivata produsului – funcții exponențiale", "hard")
def gen_s3_ex1_deriv_exp(rng=random):
    a = rng.randint(1, 4)
    text = (f"Se consideră $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = (x - {a})e^x$.\n\n"
            f"a) Arătați că $f'(x) = (x - {a-1})e^x$.\n\n"
            f"b) Determinați asimptota orizontală spre $-\\infty$.\n\n"
            f"c) Demonstrați că $f(x) \\geq -e^{{{a-1}}}$ pe $\\mathbb{{R}}$.")
    solution = (f"a) $f'(x) = e^x + (x-{a})e^x = (x-{a-1})e^x$.\n\n"
                f"b) $\\lim_{{x \\to -\\infty}}(x-{a})e^x = 0$. Asimptotă: $y=0$.\n\n"
                f"c) $f'(x)=0 \\Rightarrow x={a-1}$ (minim). $f({a-1}) = -e^{{{a-1}}}$.")
    return {"id": "s3_ex1_deriv_exp", "text": text, "solution": solution,
            "points": 15, "params": {"a": a}, "lesson": "Derivate"}

@registry.register(slot=9)
@template("s3_derivative_rational_monotonicity", "Derivata fracției raționale – monotonie", "hard")
def gen_s3_ex1_deriv_rational(rng=random):
    a = rng.randint(1, 5)
    b = rng.randint(1, 4)
    text = (f"Se consideră $f: (-{b}, \\infty) \\to \\mathbb{{R}}$, $f(x) = \\frac{{x - {a}}}{{x + {b}}}$.\n\n"
            f"a) Arătați că $f'(x) = \\frac{{{a+b}}}{{(x+{b})^2}}$.\n\n"
            f"b) Determinați asimptota orizontală spre $+\\infty$.\n\n"
            f"c) Demonstrați că $f(x) \\lt 1$ pe $(-{b}, \\infty)$.")
    solution = (f"a) $f'(x) = \\frac{{(x+{b})-(x-{a})}}{{(x+{b})^2}} = \\frac{{{a+b}}}{{(x+{b})^2}}$.\n\n"
                f"b) $\\lim_{{x\\to\\infty}} f(x) = 1$. Asimptotă: $y=1$.\n\n"
                f"c) $f(x)\\lt 1 \\iff x-{a}\\lt x+{b} \\iff -{a}\\lt {b}$ ✓.")
    return {"id": "s3_ex1_deriv_rational", "text": text, "solution": solution,
            "points": 15, "params": {"a": a, "b": b}, "lesson": "Derivate"}

@registry.register(slot=9)
@template("s3_derivative_second_order_convexity", "Derivata de ordinul doi – convexitate", "hard")
def gen_s3_ex1_deriv_convexity(rng=random):
    a = rng.randint(1, 3)
    b = rng.randint(1, 4)
    text = (f"Se consideră $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = {a}x^3 - {b}x^2$.\n\n"
            f"a) Calculați $f'(x)$ și $f''(x)$.\n\n"
            f"b) Determinați intervalele de convexitate și concavitate.\n\nc) Găsiți punctul de inflexiune.")
    ip_x = b / (3 * a)
    ip_y = a * ip_x**3 - b * ip_x**2
    solution = (f"a) $f'(x) = {3*a}x^2 - {2*b}x$; $f''(x) = {6*a}x - {2*b}$.\n\n"
                f"b) $f''(x) \\gt 0 \\Rightarrow x \\gt \\frac{{{2*b}}}{{{6*a}}} = \\frac{{{b}}}{{{3*a}}}$ (convex); "
                f"$x \\lt \\frac{{{b}}}{{{3*a}}}$ (concav).\n\n"
                f"c) Punct de inflexiune: $x_0 = \\frac{{{b}}}{{{3*a}}}$.")
    return {"id": "s3_ex1_deriv_convexity", "text": text, "solution": solution,
            "points": 15, "params": {"a": a, "b": b, "ip_x_num": b, "ip_x_den": 3*a}, "lesson": "Derivate"}

@registry.register(slot=9)
@template("s3_derivative_implicit_tangent", "Tangenta la graficul unei funcții implicite", "hard")
def gen_s3_ex1_deriv_implicit(rng=random):
    a = rng.randint(2, 4)
    x0 = rng.randint(0, 2)
    y0 = a * x0**2 + 1
    slope = 2 * a * x0
    text = (f"Se consideră $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = {a}x^2 + 1$.\n\n"
            f"a) Calculați $f'(x)$.\n\n"
            f"b) Determinați ecuația tangentei la grafic în punctul de abscisă $x_0 = {x0}$.\n\n"
            f"c) Arătați că $f(x) \\geq 1$ pentru orice $x \\in \\mathbb{{R}}$.")
    solution = (f"a) $f'(x) = {2*a}x$.\n\n"
                f"b) $f({x0}) = {y0}$, $f'({x0}) = {slope}$. Tangenta: $y - {y0} = {slope}(x - {x0})$.\n\n"
                f"c) ${a}x^2 \\geq 0 \\Rightarrow f(x) = {a}x^2 + 1 \\geq 1$.")
    return {"id": "s3_ex1_deriv_implicit", "text": text, "solution": solution,
            "points": 15, "params": {"a": a, "x0": x0, "y0": y0, "slope": slope}, "lesson": "Derivate"}

def gen_s3_ex1(rng=random):
    return rng.choice(registry.get_generators(9))(rng)


# ─────────────────────────────── Slot 10 ───────────────────────────────

@registry.register(slot=10)
@template("s3_integral_polynomial_volume", "Integrale definite – polinoame, volum de rotație", "hard")
def gen_s3_ex2_int_poly(rng=random):
    a = rng.randint(1, 5)
    text = (f"Se consideră $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = x^2 + {a}$.\n\n"
            f"a) Arătați că $\\int_0^1 (f(x)-{a})\\,dx = \\frac{{1}}{{3}}$.\n\n"
            f"b) Arătați că $\\int_0^1 e^x(f(x)-x^2)\\,dx = {a}(e-1)$.\n\n"
            f"c) Calculați volumul corpului obținut prin rotația graficului $g(x) = \\sqrt{{f(x)-{a}}}$ în jurul $Ox$.")
    solution = (f"a) $\\int_0^1 x^2\\,dx = \\frac{{1}}{{3}}$.\n\n"
                f"b) $\\int_0^1 {a}e^x\\,dx = {a}(e-1)$.\n\n"
                f"c) $V = \\pi\\int_0^1 x^2\\,dx = \\frac{{\\pi}}{{3}}$.")
    return {"id": "s3_ex2_int_poly", "text": text, "solution": solution,
            "points": 15, "params": {"a": a}, "lesson": "Limite"}

@registry.register(slot=10)
@template("s3_integral_logarithmic_fraction", "Integrala fracției logaritmice prin substituție", "hard")
def gen_s3_ex2_int_frac(rng=random):
    text = (f"Se consideră $f: (0,\\infty) \\to \\mathbb{{R}}$, $f(x) = \\frac{{\\ln x}}{{x}}$.\n\n"
            f"a) Arătați că $\\int_1^e f(x)\\cdot x\\,dx = 1$.\n\n"
            f"b) Arătați că orice primitivă $F$ a lui $f$ este convexă pe $(0, e]$.\n\n"
            f"c) Calculați $\\int_1^e f(x)\\,dx$.")
    solution = ("a) $\\int_1^e \\ln x\\,dx = [x\\ln x - x]_1^e = (e-e)-(-1) = 1$.\n\n"
                "b) $F''(x) = f'(x) = \\frac{1-\\ln x}{x^2} \\geq 0$ pe $(0,e]$ ✓\n\n"
                "c) Substituție $t = \\ln x$: $\\int_0^1 t\\,dt = \\frac{1}{2}$.")
    return {"id": "s3_ex2_int_frac", "text": text, "solution": solution,
            "points": 15, "params": {}, "lesson": "Limite"}

@registry.register(slot=10)
@template("s3_integral_rational_log_substitution", "Integrala funcției raționale prin substituție logaritmică", "hard")
def gen_s3_ex2_int_rational_log(rng=random):
    a = rng.randint(1, 5)
    text = (f"Se consideră $f: \\mathbb{{R}} \\to \\mathbb{{R}}$, $f(x) = \\frac{{x}}{{x^2+{a}}}$.\n\n"
            f"a) Arătați că $\\int_0^1 (x^2+{a})f(x)\\,dx = \\frac{{1}}{{2}}$.\n\n"
            f"b) Arătați că $\\int_0^{{\\sqrt{{{a}}}}} f(x)\\,dx = \\frac{{1}}{{2}}\\ln 2$.\n\n"
            f"c) Arătați că $\\int_0^1 f(x)\\,dx = \\frac{{1}}{{2}}\\ln\\frac{{{a+1}}}{{{a}}}$.")
    solution = (f"a) $\\int_0^1 x\\,dx = \\frac{{1}}{{2}}$.\n\n"
                f"b) $t = x^2+{a}$: $\\int_{{{a}}}^{{{2*a}}} \\frac{{1}}{{2t}}dt = \\frac{{1}}{{2}}\\ln 2$.\n\n"
                f"c) Același $t$: $\\int_{{{a}}}^{{{a+1}}} \\frac{{1}}{{2t}}dt = \\frac{{1}}{{2}}\\ln\\frac{{{a+1}}}{{{a}}}$.")
    return {"id": "s3_ex2_int_rational_log", "text": text, "solution": solution,
            "points": 15, "params": {"a": a}, "lesson": "Limite"}

@registry.register(slot=10)
@template("s3_integral_by_parts_exponential", "Integrare prin părți – funcții exponențiale", "hard")
def gen_s3_ex2_int_by_parts(rng=random):
    n = rng.randint(1, 3)
    text = (f"Calculați $I_n = \\int_0^1 x^{n} e^x\\,dx$ pentru $n = {n}$.")
    # Compute I_n by parts: I_n = e - n*I_{n-1}, I_0 = e-1
    i0 = "e-1"
    if n == 1:
        result = "e - (e-1) = 1"
    elif n == 2:
        result = "e - 2(e-1-0) = e - 2"
    else:
        result = f"calculat prin reducere la $I_{{n-1}}$"
    solution = (f"Prin integrare prin părți ($u = x^{n}$, $dv = e^x dx$):\n"
                f"$I_{{{n}}} = [x^{n} e^x]_0^1 - {n} I_{{{n-1}}} = e - {n} I_{{{n-1}}}$.\n"
                f"$I_0 = \\int_0^1 e^x\\,dx = e-1$. Rezultat: $I_{{{n}}} = {result}$.")
    return {"id": "s3_ex2_int_by_parts", "text": text, "solution": solution,
            "points": 15, "params": {"n": n}, "lesson": "Limite"}

@registry.register(slot=10)
@template("s3_integral_area_between_curves", "Aria suprafeței dintre două curbe", "hard")
def gen_s3_ex2_int_area(rng=random):
    a = rng.randint(1, 3)
    b = rng.randint(a+1, a+3)
    text = (f"Calculați aria suprafeței mărginite de graficele funcțiilor "
            f"$f(x) = x^2$ și $g(x) = {a+b}x - {a*b}$.")
    # Intersection: x^2 = (a+b)x - ab => x^2 - (a+b)x + ab = 0 => (x-a)(x-b)=0
    # Area = integral from a to b of (g-f) = integral of -(x^2-(a+b)x+ab)
    area = (b - a)**3 / 6
    solution = (f"Intersecții: $x^2 = {a+b}x - {a*b} \\Rightarrow x_1 = {a}$, $x_2 = {b}$.\n"
                f"Aria = $\\int_{{{a}}}^{{{b}}} ({a+b}x - {a*b} - x^2)\\,dx = "
                f"\\frac{{({b}-{a})^3}}{{6}} = \\frac{{{(b-a)**3}}}{{6}}$.")
    return {"id": "s3_ex2_int_area", "text": text, "solution": solution,
            "points": 15, "params": {"a": a, "b": b, "area_num": (b-a)**3, "area_den": 6}, "lesson": "Limite"}

def gen_s3_ex2(rng=random):
    return rng.choice(registry.get_generators(10))(rng)
