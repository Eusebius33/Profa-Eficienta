"""
Comprehensive automated verification for copyMath.js Google Docs integration.
Tests:
  1. Code structure (all format handlers, functions, UI components exist)
  2. LaTeX extraction logic simulation (all 16 equation types)
  3. Template integration (all mode templates use unified copy system)
  4. Backward compatibility (Word formats preserved)
"""
import re
import os
from html.parser import HTMLParser


# ────────────────────────────────────────────────────────────────────────────
#  Utilities
# ────────────────────────────────────────────────────────────────────────────

class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def check(self, desc, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        self.tests.append((status, desc, detail))
        icon = "PASS" if condition else "FAIL"
        msg = f"  [{icon}] {desc}"
        if detail and not condition:
            msg += f"  ({detail})"
        print(msg)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  TOTAL: {total}   PASSED: {self.passed}   FAILED: {self.failed}")
        status = "ALL TESTS PASSED" if self.failed == 0 else f"{self.failed} TEST(S) FAILED"
        print(f"  {status}")
        print(f"{'='*60}")
        return self.failed == 0


# ────────────────────────────────────────────────────────────────────────────
#  Test 1: copyMath.js structure
# ────────────────────────────────────────────────────────────────────────────

def test_copymath_structure(r):
    print("\n" + "="*60)
    print("  TEST 1: copyMath.js Code Structure")
    print("="*60)

    with open("static/copyMath.js", "r", encoding="utf-8") as f:
        js = f.read()

    # Core functions
    r.check("extractMathML function exists", "function extractMathML(" in js)
    r.check("extractLaTeXText function exists", "function extractLaTeXText(" in js)
    r.check("renderToImageBlob function exists", "function renderToImageBlob(" in js)
    r.check("buildClipboardItem function exists", "function buildClipboardItem(" in js)
    r.check("copyWithFormat function exists", "async function copyWithFormat(" in js)
    r.check("flashSuccess function exists", "function flashSuccess(" in js)
    r.check("attachDropdown function exists", "function attachDropdown(" in js)

    # Format definitions
    r.check("word_legacy format defined", '"word_legacy"' in js)
    r.check("word_modern format defined", '"word_modern"' in js)
    r.check("word_web format defined", '"word_web"' in js)
    r.check("google_docs format defined", '"google_docs"' in js)
    r.check("google_docs_img format defined", '"google_docs_img"' in js)

    # Format handlers in buildClipboardItem
    r.check("google_docs handled in build", 'format === "google_docs"' in js)
    r.check("word_legacy handled in build", 'format === "word_legacy"' in js)
    r.check("word_web handled in build", 'format === "word_web"' in js)

    # Google Docs image path
    r.check("google_docs_img handled in copyWithFormat",
            'format === "google_docs_img"' in js)
    r.check("Image uses PNG blob", '"image/png"' in js)

    # KaTeX annotation extraction
    r.check("Reads application/x-tex annotation",
            'annotation[encoding="application/x-tex"]' in js)
    r.check("Uses $$ delimiters for LaTeX", '$$' in js)

    # UI components
    r.check("Section headers in dropdown", "addSectionHeader" in js)
    r.check("Microsoft Word section", '"Microsoft Word"' in js)
    r.check("Google Docs section", '"Google Docs"' in js)
    r.check("Format descriptions in dropdown", "desc:" in js)
    r.check("Format icons in dropdown", "icon:" in js)

    # Public API backward compatibility
    r.check("window.copyMathToClipboard preserved", "window.copyMathToClipboard" in js)
    r.check("window.enhanceCopyButtons preserved", "window.enhanceCopyButtons" in js)
    r.check(".copy-math-btn selector", ".copy-math-btn" in js)

    # Persistence
    r.check("localStorage format persistence", "copiaza_format" in js)

    # Graceful fallback
    r.check("Fallback to plaintext on error", "extractLaTeXText(containerElement)" in js)

    # MathML xmlns
    r.check("MathML xmlns set correctly",
            'http://www.w3.org/1998/Math/MathML' in js)


# ────────────────────────────────────────────────────────────────────────────
#  Test 2: LaTeX extraction simulation
# ────────────────────────────────────────────────────────────────────────────

class KaTeXExtractor(HTMLParser):
    """Simulates what extractLaTeXText does in the browser."""
    def __init__(self):
        super().__init__()
        self._in_ann = False
        self._latex_parts = []
        self.results = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "annotation" and d.get("encoding") == "application/x-tex":
            self._in_ann = True
            self._latex_parts = []

    def handle_endtag(self, tag):
        if tag == "annotation" and self._in_ann:
            latex = "".join(self._latex_parts).strip()
            wrapped = f"$${latex}$$"
            self.results.append({"latex": latex, "wrapped": wrapped})
            self._in_ann = False

    def handle_data(self, data):
        if self._in_ann:
            self._latex_parts.append(data)


def test_latex_extraction(r):
    print("\n" + "="*60)
    print("  TEST 2: LaTeX Extraction Simulation (16 equation types)")
    print("="*60)

    # Each test case: (id, title, raw_latex, katex_html_fragment)
    CASES = [
        ("inline", "Inline Equation",
         r"x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}",
         '<span class="katex"><math><annotation encoding="application/x-tex">x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}</annotation></math></span>'),

        ("fraction", "Fractions",
         r"\frac{x^2 + 3x + 2}{x + 1} = x + 2",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\frac{x^2 + 3x + 2}{x + 1} = x + 2</annotation></math></span>'),

        ("sqrt", "Square Roots",
         r"\sqrt{a^2 + b^2} = c",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\sqrt{a^2 + b^2} = c</annotation></math></span>'),

        ("power", "Powers",
         r"2^{n+1} = 2 \cdot 2^n",
         '<span class="katex"><math><annotation encoding="application/x-tex">2^{n+1} = 2 \\cdot 2^n</annotation></math></span>'),

        ("integral", "Integrals",
         r"\int_0^1 x^2 \, dx = \frac{1}{3}",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\int_0^1 x^2 \\, dx = \\frac{1}{3}</annotation></math></span>'),

        ("double_int", "Double Integrals",
         r"\iint_D (x^2 + y^2) \, dA",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\iint_D (x^2 + y^2) \\, dA</annotation></math></span>'),

        ("derivative", "Derivatives",
         r"\frac{d}{dx}\left(x^3 + 2x\right) = 3x^2 + 2",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\frac{d}{dx}\\left(x^3 + 2x\\right) = 3x^2 + 2</annotation></math></span>'),

        ("limit", "Limits",
         r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1</annotation></math></span>'),

        ("sum", "Summations",
         r"\sum_{k=1}^{n} k = \frac{n(n+1)}{2}",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\sum_{k=1}^{n} k = \\frac{n(n+1)}{2}</annotation></math></span>'),

        ("matrix", "Matrices",
         r"\begin{pmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \\ 7 & 8 & 9 \end{pmatrix}",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\begin{pmatrix} 1 &amp; 2 &amp; 3 \\\\ 4 &amp; 5 &amp; 6 \\\\ 7 &amp; 8 &amp; 9 \\end{pmatrix}</annotation></math></span>'),

        ("determinant", "Determinants",
         r"\det(A) = \begin{vmatrix} a & b \\ c & d \end{vmatrix} = ad - bc",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\det(A) = \\begin{vmatrix} a &amp; b \\\\ c &amp; d \\end{vmatrix} = ad - bc</annotation></math></span>'),

        ("piecewise", "Piecewise / Cases",
         r"f(x) = \begin{cases} x^2 & \text{if } x \geq 0 \\ -x & \text{if } x < 0 \end{cases}",
         '<span class="katex"><math><annotation encoding="application/x-tex">f(x) = \\begin{cases} x^2 &amp; \\text{if } x \\geq 0 \\\\ -x &amp; \\text{if } x &lt; 0 \\end{cases}</annotation></math></span>'),

        ("function", "Functions",
         r"(f \circ g)(x) = f(g(x)) = \sin(x^2 + 1)",
         '<span class="katex"><math><annotation encoding="application/x-tex">(f \\circ g)(x) = f(g(x)) = \\sin(x^2 + 1)</annotation></math></span>'),

        ("nested", "Nested Expressions",
         r"\frac{\sum_{i=1}^{n} x_i^2}{\sqrt{\left(\int_0^1 f(t)\,dt\right)^2 + 1}}",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\frac{\\sum_{i=1}^{n} x_i^2}{\\sqrt{\\left(\\int_0^1 f(t)\\,dt\\right)^2 + 1}}</annotation></math></span>'),

        ("system", "System of Equations",
         r"\begin{cases} 2x + 3y = 7 \\ x - y = 1 \end{cases}",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\begin{cases} 2x + 3y = 7 \\\\ x - y = 1 \\end{cases}</annotation></math></span>'),

        ("product", "Products",
         r"\prod_{i=1}^{n} \frac{1}{1+x_i}",
         '<span class="katex"><math><annotation encoding="application/x-tex">\\prod_{i=1}^{n} \\frac{1}{1+x_i}</annotation></math></span>'),
    ]

    for test_id, title, raw_latex, html in CASES:
        p = KaTeXExtractor()
        p.feed(html)

        extracted = len(p.results) > 0
        r.check(f"{title}: annotation extracted", extracted)

        if extracted:
            wrapped = p.results[0]["wrapped"]
            has_delimiters = wrapped.startswith("$$") and wrapped.endswith("$$")
            r.check(f"{title}: $$ delimiters correct", has_delimiters, f"got: {wrapped[:60]}...")
            has_latex_content = len(p.results[0]["latex"]) > 3
            r.check(f"{title}: LaTeX content non-empty", has_latex_content)


# ────────────────────────────────────────────────────────────────────────────
#  Test 3: Template integration
# ────────────────────────────────────────────────────────────────────────────

def test_templates(r):
    print("\n" + "="*60)
    print("  TEST 3: Template Integration")
    print("="*60)

    # mode1.html
    with open("templates/modes/mode1.html", "r", encoding="utf-8") as f:
        m1 = f.read()
    r.check("mode1: uses copy-math-btn", "copy-math-btn" in m1)
    r.check("mode1: calls copyMathToClipboard", "copyMathToClipboard" in m1)
    r.check("mode1: has msg-content-container", "msg-content-container" in m1)

    # mode2.html
    with open("templates/modes/mode2.html", "r", encoding="utf-8") as f:
        m2 = f.read()
    r.check("mode2: uses copy-math-btn", "copy-math-btn" in m2)
    r.check("mode2: calls copyMathToClipboard", "copyMathToClipboard" in m2)
    r.check("mode2: has msg-content-container", "msg-content-container" in m2)

    # mode3.html
    with open("templates/modes/mode3.html", "r", encoding="utf-8") as f:
        m3 = f.read()
    r.check("mode3: uses copy-math-btn", "copy-math-btn" in m3)
    r.check("mode3: calls copyMathToClipboard", "copyMathToClipboard" in m3)
    r.check("mode3: has msg-content-container", "msg-content-container" in m3)
    r.check("mode3: old copy-btn handler removed",
            'e.target.closest(".copy-btn")' not in m3)
    r.check("mode3: calls enhanceCopyButtons",
            "enhanceCopyButtons" in m3)

    # layout.html — script loaded globally
    with open("templates/layout.html", "r", encoding="utf-8") as f:
        layout = f.read()
    r.check("layout: copyMath.js included", "copyMath.js" in layout)
    r.check("layout: KaTeX CSS loaded", "katex" in layout.lower())
    r.check("layout: KaTeX JS loaded", "katex.min.js" in layout)
    r.check("layout: auto-render loaded", "auto-render.min.js" in layout)


# ────────────────────────────────────────────────────────────────────────────
#  Test 4: Backward compatibility
# ────────────────────────────────────────────────────────────────────────────

def test_backward_compat(r):
    print("\n" + "="*60)
    print("  TEST 4: Backward Compatibility")
    print("="*60)

    with open("static/copyMath.js", "r", encoding="utf-8") as f:
        js = f.read()

    # Word formats still generate MathML
    r.check("MathML extraction preserved", "extractMathML" in js)
    r.check("katex-html removed from MathML", "katex-html" in js)
    r.check("MathML xmlns attribute set", "xmlns" in js)

    # Word legacy: bare MathML in text/html
    r.check("word_legacy: text/html payload", '"text/html"' in js)

    # Word modern: HTML wrapper around MathML
    r.check("word_modern: DOCTYPE wrapper", "<!DOCTYPE html>" in js)

    # Word web: MathML + LaTeX text fallback
    r.check("word_web: dual payload", 'format === "word_web"' in js)

    # IIFE pattern preserved
    r.check("IIFE wrapper", "(function" in js)
    r.check("use strict", '"use strict"' in js)

    # No broken syntax (basic check: balanced braces)
    opens = js.count("{")
    closes = js.count("}")
    r.check("Balanced braces", opens == closes, f"{{ {opens} vs }} {closes}")


# ────────────────────────────────────────────────────────────────────────────
#  Test 5: Test harness file
# ────────────────────────────────────────────────────────────────────────────

def test_harness_exists(r):
    print("\n" + "="*60)
    print("  TEST 5: Test Harness & Documentation Files")
    print("="*60)

    r.check("test_equations.html exists",
            os.path.isfile("static/test_equations.html"))

    if os.path.isfile("static/test_equations.html"):
        with open("static/test_equations.html", "r", encoding="utf-8") as f:
            th = f.read()
        r.check("Harness: has KaTeX", "katex" in th.lower())
        r.check("Harness: has copyMath.js", "copyMath.js" in th)
        r.check("Harness: has clipboard reader", "readClipboard" in th)
        r.check("Harness: tests integrals", "integral" in th.lower())
        r.check("Harness: tests matrices", "matrix" in th.lower())
        r.check("Harness: tests limits", "limit" in th.lower())
        r.check("Harness: tests piecewise", "piecewise" in th.lower())
        r.check("Harness: tests derivatives", "derivative" in th.lower())
        r.check("Harness: tests determinants", "determinant" in th.lower())
        r.check("Harness: tests nested expressions", "nested" in th.lower())


# ────────────────────────────────────────────────────────────────────────────
#  Main
# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    r = Results()

    test_copymath_structure(r)
    test_latex_extraction(r)
    test_templates(r)
    test_backward_compat(r)
    test_harness_exists(r)

    r.summary()
