"""
Official BAC exam reference data for duplicate detection.

Each exercise now includes both 'id' (legacy) and 'template_id' (v3 architecture).
This ensures Level-3 template-position duplicate detection works correctly against
official papers.
"""

def _ex(eid, template_id, text):
    return {"id": eid, "template_id": template_id, "text": text, "param_signature": ""}

OFFICIAL_EXAMS = [
    # Exam 1 — 2023 Subiect 06
    [
        _ex("s1_ex1_prog_arith",       "s1_arith_seq_nth_term",          "Determinați al patrulea termen al progresiei aritmetice (a_n) știind că a_1 = 2 și d = 3"),
        _ex("s1_ex2_parabola_vertex",  "s1_parabola_vertex",             "Determinați coordonatele vârfului parabolei f(x) = x^2 - 4x + 3"),
        _ex("s1_ex3_eq_radical",       "s1_radical_equation",            "Rezolvați în mulțimea numerelor reale ecuația \\sqrt{2x + 1} = 3"),
        _ex("s1_ex4_prob",             "s1_classical_probability",       "Calculați probabilitatea ca un număr de două cifre ales aleatoriu să fie divizibil cu 7"),
        _ex("s1_ex5_midpoint",         "s1_midpoint_segment",            "În reperul xOy punctele A(2,3) și B(6,5). Determinați mijlocul AB"),
        _ex("s1_ex6_law_cos",          "s1_law_of_cosines",              "Triunghiul ABC cu AB=8, AC=5 și cos A=1/2. Calculați BC"),
        _ex("s2_ex1_mat_param",        "s2_matrix_parametric_power",     "Matricea A(x) = diag(1,1,2^x) parametrizată"),
        _ex("s2_ex2_law_absorb",       "s2_law_absorbing_element",       "Legea x * y = xy - 3(x+y) + 12"),
        _ex("s3_ex1_deriv_log",        "s3_derivative_log_product",      "Funcția f(x) = x ln x - 2x"),
        _ex("s3_ex2_int_poly",         "s3_integral_polynomial_volume",  "Funcția f(x) = x^2 + 3"),
    ],
    # Exam 2 — 2024 Subiect 09
    [
        _ex("s1_ex1_prog_geom",        "s1_geom_seq_nth_term",           "Determinați al treilea termen al progresiei geometrice cu b_1=2, q=3"),
        _ex("s1_ex2_func_intersect",   "s1_func_graph_intersection",     "Intersecția graficelor f(x)=x^2-3x+2 și g(x)=x-1"),
        _ex("s1_ex3_eq_exponential",   "s1_exponential_equation",        "Ecuația 2^{3x-1}=32"),
        _ex("s1_ex4_comb",             "s1_combinatorics_CnA",           "Calculați C_5^2 - A_4^2"),
        _ex("s1_ex5_parallel_line",    "s1_parallel_line_through_point", "Dreapta paralelă cu 2x-y+3=0 prin A(1,1)"),
        _ex("s1_ex6_area",             "s1_triangle_area_formula",       "Aria triunghiului ABC cu AB=6, AC=8, m(A)=30°"),
        _ex("s2_ex1_mat_symmetric",    "s2_matrix_symmetric_determinant","Matricea A(a) = [[a,1,1],[1,a,1],[1,1,a]]"),
        _ex("s2_ex2_law_assoc",        "s2_law_associative_exponential", "Legea x * y = x + y - 4"),
        _ex("s3_ex1_deriv_exp",        "s3_derivative_exponential_product","Funcția f(x)=(x-2)e^x"),
        _ex("s3_ex2_int_frac",         "s3_integral_logarithmic_fraction","Funcția f(x) = ln(x)/x"),
    ],
    # Exam 3 — 2024 Simulare
    [
        _ex("s1_ex1_calc",             "s1_radical_integer",             "Arătați că N = (3-sqrt(2))^2 + 6sqrt(2) este întreg"),
        _ex("s1_ex2_func_product",     "s1_func_zero_product",           "f(x)=x-3, calculați f(1)·f(2)···f(10)"),
        _ex("s1_ex3_eq_logarithmic",   "s1_logarithmic_equation",        "Ecuația log_2(2x+4)=4"),
        _ex("s1_ex4_finance",          "s1_percentage_price",            "Scumpire cu 10%, prețul crește cu 20 lei"),
        _ex("s1_ex5_vectors",          "s1_collinear_vectors_condition",  "Vectorii u=mi+4j și v=2i+8j coliniari"),
        _ex("s1_ex6_trig_calc",        "s1_trig_special_values",         "E = 2sin30 - 2cos60 + 4sin90 este natural"),
        _ex("s2_ex1_mat_nilpotent",    "s2_matrix_nilpotent_inverse",    "A(x) triunghiulară superioară, B(x)=A(x)-I nilpotent"),
        _ex("s2_ex2_law_linear_quadratic","s2_law_product_quadratic",    "Legea x*y = xy + x + y"),
        _ex("s3_ex1_deriv_rational",   "s3_derivative_rational_monotonicity","f(x)=(x-1)/(x+2)"),
        _ex("s3_ex2_int_rational_log", "s3_integral_rational_log_substitution","f(x) = x/(x^2+2)"),
    ],
]
