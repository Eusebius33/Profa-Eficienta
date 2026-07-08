import re
from bac_generator.validators.sympy_verify import sympy_verify_exercise

def verify_exercise(exercise: dict) -> bool:
    """
    Combines basic syntax/bounds checks with advanced symbolic validation using SymPy.
    """
    text_content = exercise.get("text", "") + " " + exercise.get("solution", "")
    
    # Simple syntax validation: check brackets balance
    if text_content.count('{') != text_content.count('}'):
        return False
    if text_content.count('(') != text_content.count(')'):
        return False
        
    # Check for obvious division by zero in LaTeX
    div_zero_patterns = [
        r"\\frac\{[^}]*\}\{0\}",
        r"/\s*0\b"
    ]
    for pattern in div_zero_patterns:
        if re.search(pattern, text_content):
            return False
            
    # Parameter boundary bounds validation
    params = exercise.get("params", {})
    for key, val in params.items():
        if "denom" in key and val == 0:
            return False
        if "log_arg" in key and val <= 0:
            return False
        if "log_base" in key and (val <= 0 or val == 1):
            return False
        if "sqrt_val" in key and val < 0:
            return False
            
    # Run SymPy checks
    return sympy_verify_exercise(exercise)
