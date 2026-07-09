from .registry import registry
from . import algebra, geometry, matrices, algebra_structures, calculus

# Explicitly expose backward-compatible generator functions
from .algebra import gen_s1_ex1, gen_s1_ex2, gen_s1_ex3, gen_s1_ex4
from .geometry import gen_s1_ex5, gen_s1_ex6
from .matrices import gen_s2_ex1
from .algebra_structures import gen_s2_ex2
from .calculus import gen_s3_ex1, gen_s3_ex2
