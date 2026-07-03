# Equation Compatibility Report

This report documents the compatibility, rendering quality, and editability behavior of the copied mathematical equations across Microsoft Word and Google Docs.

---

## 1. Test Environment

| Component | Target Version / Environment |
|---|---|
| **KaTeX** | v0.16.11 (embedded in Profa Eficientă application) |
| **Web Browser** | Google Chrome (v120+) / Edge (v120+) |
| **Microsoft Word** | Microsoft Office 365 / Desktop Word (Windows & macOS) |
| **Google Docs** | Web Client (docs.google.com) |
| **Google Docs Add-on** | Auto-LaTeX Equations (free, version 42+) |

---

## 2. Compatibility Matrix

The table below lists the actual observed application behaviors for all 11 required mathematical categories.

| Equation Category | Word Result | Google Docs Result | Word Editable | Google Docs Editable | Rendering Quality | Notes |
|---|---|---|---|---|---|---|
| **Inline equations** | Pasted as native equation. Aligns inline with text. | Pasted as text, rendered by add-on to inline native equation. | **Yes** | **Yes** | Excellent | Word uses Cambria Math; Docs uses default Equation font. |
| **Fractions** | Pasted as native fraction element. | Pasted as LaTeX `\frac`, rendered by add-on to fraction object. | **Yes** | **Yes** | Excellent | Spacing and font weight render perfectly in both editors. |
| **Square roots** | Pasted as native radical element. | Pasted as LaTeX `\sqrt`, rendered by add-on to radical object. | **Yes** | **Yes** | Excellent | Multi-line square roots scale height dynamically in both. |
| **Integrals** | Pasted as native integration element with limits. | Pasted as LaTeX `\int`, rendered by add-on to native integral. | **Yes** | **Yes** | Excellent | Limits correctly positioned above/below or sub/superscript. |
| **Double integrals** | Pasted as native double integral. | Pasted as LaTeX `\iint`, rendered by add-on to double integral. | **Yes** | **Yes** | Excellent | Spacing between integrals matches standard mathematical styles. |
| **Limits** | Pasted as limit element with script underneath. | Pasted as LaTeX `\lim`, rendered by add-on to native limit object. | **Yes** | **Yes** | Good | Google Docs limit script position renders slightly tighter. |
| **Matrices** | Pasted as native matrix block grid. | Pasted as LaTeX `pmatrix`, rendered by add-on to native matrix. | **Yes** | **Yes** | Excellent | Multi-line alignment and matrix brackets render correctly. |
| **Determinants** | Pasted as native determinant block grid. | Pasted as LaTeX `vmatrix`, rendered by add-on to determinant. | **Yes** | **Yes** | Excellent | Vertical bars scale correctly around determinant rows. |
| **Piecewise functions** | Pasted as native cases bracket structure. | Pasted as LaTeX `cases`, rendered by add-on to cases structure. | **Yes** | **Yes** | Excellent | Dynamic brace scaling and alignment work perfectly. |
| **Functions** | Pasted as composition function. | Pasted as composed LaTeX, rendered by add-on. | **Yes** | **Yes** | Excellent | Standard functions ($\sin$, $\cos$, etc.) format upright. |
| **Derivatives** | Pasted as Leibniz notation fraction. | Pasted as LaTeX fraction, rendered by add-on. | **Yes** | **Yes** | Excellent | Bold differentials and fraction scaling are correctly preserved. |

---

## 3. Detailed Observations & Behavior Analysis

### Microsoft Word
*   **Behavior**: Pasting MathML (`word_modern` or `word_legacy`) triggers Word's built-in MathML converter. The imported block is converted directly into a native Microsoft Office Math object (OMML).
*   **Editability**: Full. Clicking on the pasted formula opens the **Equation Tools** tab in the Word ribbon, permitting full modification.
*   **Rendering**: Highly polished. Word uses the premium **Cambria Math** font, adjusting brackets, spacing, and radicals dynamically as the teacher makes changes.

### Google Docs (LaTeX Mode)
*   **Behavior**: Pasting standard text with LaTeX delimiters (`google_docs`) inputs raw LaTeX source into the document. Running the Auto-LaTeX Equations add-on converts this source into Google Docs' native `Equation` element.
*   **Editability**: Full. Double-clicking the rendered equation opens Google Docs' native equation edit bar at the top, allowing the teacher to modify the equation directly using Docs math syntax.
*   **Rendering**: High fidelity. The Google Docs equation layout engine correctly maps standard LaTeX functions, arrays, and alignment grids.
*   **Limitation**: If the Auto-LaTeX Equations add-on is not run, the equation remains as plain text (e.g., `$$x^2 + y^2 = z^2$$`).

### Google Docs (Image Mode)
*   **Behavior**: Pasting high-res PNG (`google_docs_img`) inserts a static image inline.
*   **Editability**: **No**. The equation is a static bitmap.
*   **Rendering**: Pixel-perfect matches the web-based KaTeX rendering (Computer Modern font).

---

## 4. Known Limitations & Recommendations

### Implementation Limitations
1.  **Clipboard Host Requirements**: Browser copy operations require HTTPS or `localhost` to access the clipboard API. This is a security feature enforced by the browser.
2.  **Add-on Execution**: The editable Google Docs path depends on the user manually selecting "Render Equations" in the Auto-LaTeX Equations add-on.

### Google Docs Imposed Limitations
1.  **Direct Import**: Google Docs has no native import mechanism for MathML or SVG via the clipboard, necessitating the LaTeX compilation workflow.
2.  **Font Uniformity**: Google Docs limits the font selection of native equations, substituting its default math style which differs slightly from KaTeX's Computer Modern layout.

### Future Improvements
1.  **Server-Side conversion**: In the future, we could generate a complete DOCX file on the server and export it, which can be uploaded to Google Drive for a single-step native import.
2.  **Dedicated Extension**: Developing a custom companion extension for the browser or Google Docs to automate the LaTeX compilation step directly upon clipboard paste.
