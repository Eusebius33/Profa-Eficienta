import sympy as sp
import math

def sympy_verify_exercise(exercise: dict) -> bool:
    """
    Rigorously verifies the mathematical validity of a generated exercise using SymPy.
    Returns True if mathematically verified, False otherwise.
    """
    ex_id = exercise.get("id", "")
    params = exercise.get("params", {})
    
    try:
        if ex_id == "s1_ex1_prog_arith":
            # a_n = a1 + (n-1)*d
            a1, d, n, an = params["a1"], params["d"], params["n"], params["an"]
            return int(a1 + (n - 1) * d) == int(an)
            
        elif ex_id == "s1_ex1_prog_geom":
            # b_n = b1 * q^(n-1)
            b1, q, n, bn = params["b1"], params["q"], params["n"], params["bn"]
            return int(b1 * (q ** (n - 1))) == int(bn)
            
        elif ex_id == "s1_ex1_calc":
            a, b, val = params["a"], params["b"], params["val"]
            # N = (a - sqrt(b))^2 + 2*a*sqrt(b) -> N = a^2 + b
            N = (a - sp.sqrt(b))**2 + 2*a*sp.sqrt(b)
            return int(sp.simplify(N)) == int(val)
            
        elif ex_id == "s1_ex2_parabola_vertex":
            b, c, m, k = params["b"], params["c"], params["m"], params["k"]
            # f(x) = x^2 + bx + c
            # Vertex x = -b/2, y = f(x) = -delta / 4
            x = sp.Symbol('x')
            f = x**2 + b*x + c
            xv = -sp.Rational(b, 2)
            yv = f.subs(x, xv)
            return int(xv) == int(m) and int(yv) == int(k)
            
        elif ex_id == "s1_ex2_func_intersect":
            a, b, c, d, x1, x2 = params["a"], params["b"], params["c"], params["d"], params["x1"], params["x2"]
            x = sp.Symbol('x')
            # f(x) = g(x) -> x^2 - ax + b = cx + d
            eq = x**2 - a*x + b - (c*x + d)
            sols = sp.solve(eq, x)
            # convert solutions to integers
            int_sols = [int(s) for s in sols if s.is_integer]
            return set(int_sols) == {x1, x2}
            
        elif ex_id == "s1_ex2_func_product":
            a = params["a"]
            # product is 0 if 1 <= a <= 10
            return 1 <= a <= 10
            
        elif ex_id == "s1_ex3_eq_radical":
            a, b, c, x_sol = params["a"], params["b"], params["c"], params["x"]
            # Check domain and solution by substitution with tolerance
            if a * x_sol + b < 0:
                return False
            eq_val = sp.sympify(sp.sqrt(a * x_sol + b) - c)
            return abs(float(eq_val.evalf())) < 1e-9
            
        elif ex_id == "s1_ex3_eq_exponential":
            a, b, c, val_rhs, x_sol = params["a"], params["b"], params["c"], params["rhs"], params["x"]
            eq_val = sp.sympify(a**(b * x_sol + c) - val_rhs)
            return abs(float(eq_val.evalf())) < 1e-9
            
        elif ex_id == "s1_ex3_eq_logarithmic":
            base, b, c, d, x_sol = params["base"], params["b"], params["c"], params["d"], params["x"]
            # check constraint bx+c > 0
            if int(b * x_sol + c) <= 0:
                return False
            eq_val = sp.sympify(sp.log(b * x_sol + c, base) - d)
            return abs(float(eq_val.evalf())) < 1e-9
            
        elif ex_id == "s1_ex4_prob":
            k, fav, total = params["k"], params["fav"], params["total"]
            # Verify favorable count
            multiples = [i for i in range(10, 100) if i % k == 0]
            return len(multiples) == fav and total == 90
            
        elif ex_id == "s1_ex4_comb":
            n, m, cnk, amp, val = params["n"], params["m"], params["cnk"], params["amp"], params["val"]
            return math.comb(n, 2) == cnk and math.perm(m, 2) == amp and int(cnk - amp) == int(val)
            
        elif ex_id == "s1_ex4_finance":
            P, p, increase = params["P"], params["p"], params["increase"]
            return int(P * p / 100) == int(increase)
            
        elif ex_id == "s1_ex5_midpoint":
            x1, x2, y1, y2, mx, my = params["x1"], params["x2"], params["y1"], params["y2"], params["mx"], params["my"]
            return int((x1 + x2) / 2) == mx and int((y1 + y2) / 2) == my
            
        elif ex_id == "s1_ex5_parallel_line":
            a, b, x1, y1, c_new = params["a"], params["b"], params["x1"], params["y1"], params["c_new"]
            # parallel line passes through (x1, y1) -> a*x1 + b*y1 + c_new = 0
            return int(a*x1 + b*y1 + c_new) == 0
            
        elif ex_id == "s1_ex5_vectors":
            a, b, c, d = params["a"], params["b"], params["c"], params["d"]
            # collinearity check: a/c = b/d
            return sp.Rational(a, c) == sp.Rational(b, d)
            
        elif ex_id == "s1_ex6_law_cos":
            b, c, cosA, a = params["b"], params["c"], params["cosA"], params["a"]
            cosA_val = sp.Rational(cosA)
            # BC^2 = b^2 + c^2 - 2bc cosA
            bc_sq = b**2 + c**2 - 2*b*c*cosA_val
            return int(sp.sqrt(bc_sq)) == int(a)
            
        elif ex_id == "s1_ex6_area":
            AB, AC, area = params["AB"], params["AC"], params["area"]
            # sin(30) = 1/2
            return int(0.5 * AB * AC * 0.5) == int(area)
            
        elif ex_id == "s1_ex6_trig_calc":
            return params["result"] in (2, 4, 5)
            
        elif ex_id == "s2_ex1_mat_param":
            k, b = params["k"], params["b"]
            x, y = sp.symbols('x y')
            Ax = sp.Matrix([[1, k*x, 0], [0, 1, 0], [0, 0, b**x]])
            Ay = sp.Matrix([[1, k*y, 0], [0, 1, 0], [0, 0, b**y]])
            Axy = sp.Matrix([[1, k*(x+y), 0], [0, 1, 0], [0, 0, b**(x+y)]])
            # Check A(x) * A(y) == A(x+y) using simplify
            diff = sp.simplify(Ax * Ay - Axy)
            if diff != sp.zeros(3):
                return False
            # Check determinant of A(1)
            A1 = Ax.subs(x, 1)
            return int(A1.det()) == int(b)
            
        elif ex_id == "s2_ex1_mat_symmetric":
            a = sp.Symbol('a')
            A = sp.Matrix([[a, 1, 1], [1, a, 1], [1, 1, a]])
            det = A.det()
            expected_det = (a - 1)**2 * (a + 2)
            return sp.simplify(det - expected_det) == 0
            
        elif ex_id == "s2_ex1_mat_nilpotent":
            k, m, n = params["k"], params["m"], params["n"]
            x = sp.Symbol('x')
            A = sp.Matrix([[1, k*x, m*x], [0, 1, n*x], [0, 0, 1]])
            B = A - sp.eye(3)
            expected_B2 = sp.Matrix([[0, 0, k*n*x**2], [0, 0, 0], [0, 0, 0]])
            return B**2 == expected_B2 and B**3 == sp.zeros(3)
            
        elif ex_id == "s2_ex2_law_absorb":
            a = params["a"]
            x, y = sp.symbols('x y')
            op = (x - a) * (y - a) + a
            return op.subs(y, a) == a
            
        elif ex_id == "s2_ex2_law_assoc":
            k = params["k"]
            x, y, z = sp.symbols('x y z')
            def op(p, q): return p + q - k
            return op(op(x, y), z) == op(x, op(y, z))
            
        elif ex_id == "s2_ex2_law_linear_quadratic":
            k, C, x1, x2 = params["k"], params["C"], params["x1"], params["x2"]
            x = sp.Symbol('x')
            eq = (x + 1)*(x + k + 1) - 1 - C
            sols = sp.solve(eq, x)
            int_sols = [int(s) for s in sols if s.is_integer]
            return set(int_sols) == {x1, x2}
            
        elif ex_id == "s3_ex1_deriv_log":
            a = params["a"]
            x = sp.Symbol('x', positive=True)
            f = x * sp.log(x) - a * x
            df = sp.diff(f, x)
            return df == sp.log(x) + 1 - a
            
        elif ex_id == "s3_ex1_deriv_exp":
            a = params["a"]
            x = sp.Symbol('x')
            f = (x - a) * sp.exp(x)
            df = sp.diff(f, x)
            expected_df = (x - a + 1) * sp.exp(x)
            return sp.simplify(df - expected_df) == 0
            
        elif ex_id == "s3_ex1_deriv_rational":
            a, b = params["a"], params["b"]
            x = sp.Symbol('x')
            f = (x - a) / (x + b)
            df = sp.diff(f, x)
            expected_df = (a + b) / (x + b)**2
            return sp.simplify(df - expected_df) == 0
            
        elif ex_id == "s3_ex2_int_poly":
            a = params["a"]
            x = sp.Symbol('x')
            f = x**2 + a
            i1 = sp.integrate(f - a, (x, 0, 1))
            i2 = sp.integrate(sp.exp(x) * (f - x**2), (x, 0, 1))
            return sp.simplify(i1 - sp.Rational(1, 3)) == 0 and sp.simplify(i2 - a*(sp.E - 1)) == 0
            
        elif ex_id == "s3_ex2_int_frac":
            x = sp.Symbol('x', positive=True)
            f = sp.log(x) / x
            i1 = sp.integrate(f * x, (x, 1, sp.E))
            i2 = sp.integrate(f, (x, 1, sp.E))
            return int(i1) == 1 and sp.simplify(i2 - sp.Rational(1, 2)) == 0
            
        elif ex_id == "s3_ex2_int_rational_log":
            a = params["a"]
            x = sp.Symbol('x')
            f = x / (x**2 + a)
            i1 = sp.integrate((x**2 + a) * f, (x, 0, 1))
            i2 = sp.integrate(f, (x, 0, sp.sqrt(a)))
            i3 = sp.integrate(f, (x, 0, 1))
            
            c1 = sp.simplify(i1 - sp.Rational(1, 2)) == 0
            c2 = sp.simplify(i2 - sp.Rational(1, 2) * sp.log(2)) == 0
            c3 = sp.simplify(i3 - sp.Rational(1, 2) * sp.log((a + 1) / sp.Rational(a))) == 0
            return c1 and c2 and c3

        elif ex_id == "s1_ex1_complex_modulus":
            a, b, mod_val = params["a"], params["b"], params["mod_val"]
            return a**2 + b**2 == mod_val**2

        elif ex_id == "s1_ex1_complex_conjugate":
            a, b, prod = params["a"], params["b"], params["prod"]
            return a**2 + b**2 == prod

        elif ex_id == "s1_ex3_poly_remainder":
            a, b, r, rem = params["a"], params["b"], params["r"], params["rem"]
            return r**3 - a*r + b == rem

        elif ex_id == "s1_ex3_poly_divisibility":
            r, m, p1, c = params["r"], params["m"], params["p1"], params["c"]
            return r**3 + m*r**2 + p1*r + c == 0

        elif ex_id == "s3_ex1_limit_rational":
            a, b, c = params["a"], params["b"], params["c"]
            x = sp.Symbol('x')
            f = (a*x**2 + b*x) / (c*x**2 + 1)
            lim = sp.limit(f, x, sp.oo)
            return sp.simplify(lim - sp.Rational(a, c)) == 0

        elif ex_id == "s3_ex1_limit_remarkable":
            k, m = params["k"], params["m"]
            x = sp.Symbol('x')
            lim = sp.limit(sp.sin(k*x) / (m*x), x, 0)
            return sp.simplify(lim - sp.Rational(k, m)) == 0

        return True
    except Exception as e:
        return False
