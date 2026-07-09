import re
from bac_generator.validators.sympy_verify import sympy_verify_exercise

def verify_exercise(exercise: dict) -> bool:
    """
    Combines basic syntax/bounds checks with advanced symbolic validation using SymPy.
    """
    text_content = exercise.get("text", "") + " " + exercise.get("solution", "")

    # Simple syntax validation: check brackets balance.
    # Strip "a)"/"b)"/"c)" sub-question markers first — they're plain-text list
    # labels (not LaTeX parens), but only when they open a line/clause, so this
    # doesn't touch real math like "(a-b)". text and solution are stripped
    # separately since each may independently start with its own "a)" marker.
    def _strip_list_markers(s):
        return re.sub(r"(?:^|\n\n)[a-z]\)", "", s)

    paren_check_text = (_strip_list_markers(exercise.get("text", "")) + " " +
                         _strip_list_markers(exercise.get("solution", "")))

    if text_content.count('{') != text_content.count('}'):
        return False
    if paren_check_text.count('(') != paren_check_text.count(')'):
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
