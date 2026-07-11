// copyMath.js  — Format-aware "Copiaza" clipboard handler
// =========================================================================
//
// Supports five export targets. Each one crafts a clipboard payload tuned
// for the destination editor, because no single format pastes cleanly
// into every application:
//
//   word_legacy  → "Word <2011"    : bare MathML (no HTML wrapper).
//   word_modern  → "Word >2011"    : MathML inside a minimal HTML doc.
//   word_web     → "Word web"      : MathML + LaTeX plaintext fallback.
//   google_docs  → "Google Docs"   : LaTeX in $$ delimiters. Teachers paste
//                                    into Google Docs, then run the free
//                                    Auto-LaTeX Equations add-on to render.
//   google_docs_img → "Google Docs (image)" : SVG rendered to PNG blob via
//                                    <canvas>. Pastes as a high-res image.
//                                    Non-editable last-resort fallback.
//
// The public API is backward-compatible:
//   copyMathToClipboard(btn, container)   – copies using last-selected format
//   enhanceCopyButtons(root)              – attaches dropdown to .copy-math-btn
//
// HONEST LIMITATION: Word and Google Docs re-render math in their own
// equation engines with their own fonts. Output is correct, editable and
// printable, but NOT pixel-identical to the KaTeX rendering on the site.
// =========================================================================

(function () {
  "use strict";

  const STORAGE_KEY = "copiaza_format";
  const DEFAULT_FORMAT = "google_docs_eq";

  const FORMATS = [
    { id: "word_modern",      label: "Word >2011",              icon: "📄", desc: "Editable equation in modern Word" },
    { id: "word_legacy",      label: "Word <2011",              icon: "📄", desc: "MathML for legacy Word" },
    { id: "word_web",         label: "Word Web",                icon: "🌐", desc: "Word Online / Office 365" },
    { id: "google_docs_eq",   label: "Google Docs (Ecuație)",  icon: "✏️", desc: "LaTeX pur pentru Insert › Equation" },
  ];

  // ── Persistence ──────────────────────────────────────────────────────────

  function getFormat() {
    try { return localStorage.getItem(STORAGE_KEY) || DEFAULT_FORMAT; }
    catch (e) { return DEFAULT_FORMAT; }
  }

  function setFormat(id) {
    try { localStorage.setItem(STORAGE_KEY, id); }
    catch (e) { /* private mode — ignore */ }
  }

  // ── Payload builders ─────────────────────────────────────────────────────

  /**
   * Clone container, strip KaTeX visual HTML, keep only MathML.
   * Returns { html, text } where html = raw MathML markup.
   */
  function extractMathML(containerElement) {
    const clone = containerElement.cloneNode(true);
    clone.querySelectorAll(".copy-math-btn, .copy-format-wrap").forEach(el => el.remove());

    clone.querySelectorAll("math").forEach(m => {
      m.setAttribute("xmlns", "http://www.w3.org/1998/Math/MathML");
      if (!m.hasAttribute("display")) m.setAttribute("display", "inline");
    });

    // KaTeX puts MathML in .katex-mathml, visual HTML in .katex-html.
    // Removing .katex-html leaves clean MathML for Word import.
    clone.querySelectorAll(".katex-html").forEach(el => el.remove());

    return { html: clone.innerHTML, text: clone.innerText };
  }

  /**
   * Extract original LaTeX from KaTeX annotations and wrap in delimiters
   * compatible with the Auto-LaTeX Equations Google Docs add-on.
   *
   * Display equations  → $$...$$ (newline-separated)
   * Inline  equations  → $$...$$
   *
   * Mixed text + math blocks are preserved: non-math text between equations
   * is kept verbatim so the document structure survives the paste.
   */
  function extractLaTeXText(containerElement) {
    const clone = containerElement.cloneNode(true);
    clone.querySelectorAll(".copy-math-btn, .copy-format-wrap").forEach(el => el.remove());

    // Replace each KaTeX root element with its LaTeX source.
    // Use attribute-only selector [encoding=...] — works even when the browser
    // places <annotation> in the MathML namespace (where tag-name matching can fail).
    // Wrap both inline and display equations in $$ delimiters for Auto-LaTeX Equations add-on.
    clone.querySelectorAll(".katex").forEach(katexEl => {
      // Prefer the KaTeX annotation; fall back to the raw <math> annotation
      const ann = katexEl.querySelector('[encoding="application/x-tex"]') ||
                  katexEl.querySelector('annotation');
      if (ann && ann.textContent.trim()) {
        const latex = ann.textContent.trim();
        const wrapped = `$$${latex}$$`;
        const node = document.createTextNode(wrapped);
        katexEl.parentNode.replaceChild(node, katexEl);
      }
    });

    // Fallback: raw <math> elements that might have annotations
    clone.querySelectorAll("math").forEach(m => {
      const ann = m.querySelector('[encoding="application/x-tex"]') ||
                  m.querySelector('annotation');
      if (ann && ann.textContent.trim()) {
        const latex = ann.textContent.trim();
        const wrapped = `$$${latex}$$`;
        m.parentNode.replaceChild(document.createTextNode(wrapped), m);
      } else {
        m.remove();
      }
    });

    return clone.innerText
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .trim();
  }

  /**
   * Extract LaTeX from KaTeX annotations WITHOUT any $$ delimiters.
   * Used for the google_docs_eq format — paste directly into
   * Google Docs Insert › Equation (or any equation editor that
   * accepts raw LaTeX input).
   *
   * If there are multiple equations, each is separated by a newline.
   */
  function extractRawLaTeX(containerElement) {
    const clone = containerElement.cloneNode(true);
    clone.querySelectorAll(".copy-math-btn, .copy-format-wrap").forEach(el => el.remove());

    // Track whether we found at least one KaTeX element
    let found = false;
    const latexParts = [];

    clone.querySelectorAll(".katex").forEach(katexEl => {
      const ann = katexEl.querySelector('[encoding="application/x-tex"]') ||
                  katexEl.querySelector('annotation');
      if (ann && ann.textContent.trim()) {
        found = true;
        latexParts.push(ann.textContent.trim());
        // Replace with a placeholder so innerText can reconstruct text flow
        katexEl.parentNode.replaceChild(document.createTextNode(ann.textContent.trim()), katexEl);
      }
    });

    // Fallback: raw <math>
    if (!found) {
      clone.querySelectorAll("math").forEach(m => {
        const ann = m.querySelector('[encoding="application/x-tex"]') ||
                    m.querySelector('annotation');
        if (ann && ann.textContent.trim()) {
          m.parentNode.replaceChild(document.createTextNode(ann.textContent.trim()), m);
        } else {
          m.remove();
        }
      });
    }

    return clone.innerText
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .trim();
  }

  let cachedKatexCSS = "";

  async function getKatexCSS() {
    if (cachedKatexCSS) return cachedKatexCSS;
    const katexLink = document.querySelector('link[href*="katex"]');
    const cssHref = katexLink ? katexLink.href : "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css";
    try {
      const response = await fetch(cssHref);
      if (response.ok) {
        let css = await response.text();
        css = css.replace(new RegExp("@font-face\\s*\\x7b[^\\x7d]*\\x7d", "g"), "");
        cachedKatexCSS = css;
      }
    } catch (e) {
      console.error("copyMath: failed to fetch KaTeX CSS for inlining", e);
    }
    return cachedKatexCSS;
  }

  /**
   * Render the container's math as a high-resolution PNG image blob.
   * Uses html2canvas-style approach: render KaTeX to an off-screen SVG,
   * paint it onto a <canvas>, then extract a Blob.
   *
   * Returns a Promise<Blob> (image/png).
   */
  async function renderToImageBlob(containerElement) {
    const clone = containerElement.cloneNode(true);
    clone.querySelectorAll(".copy-math-btn, .copy-format-wrap").forEach(el => el.remove());

    // Fetch CSS to inline it (ensures canvas is not tainted by external stylesheet links)
    const cssText = await getKatexCSS();

    const htmlStr = `
      <html><head>
        <meta charset="utf-8">
        <style>
          ${cssText}
          body { margin: 16px; background: white; font-size: 18px;
                 font-family: "KaTeX_Main", "Times New Roman", serif; }
          .katex-display { margin: 0.5em 0; }
        </style>
      </head><body>${clone.innerHTML}</body></html>`;

    // Use a hidden iframe to render, then paint to canvas
    const iframe = document.createElement("iframe");
    iframe.style.cssText = "position:fixed;left:-9999px;top:0;width:1200px;height:800px;border:none;";
    document.body.appendChild(iframe);

    return new Promise((resolve, reject) => {
      iframe.onload = async () => {
        try {
          // Wait for KaTeX fonts to settle
          await new Promise(r => setTimeout(r, 500));

          const body = iframe.contentDocument.body;
          const rect = body.getBoundingClientRect();
          const scale = 3; // 3x for high-DPI

          const canvas = document.createElement("canvas");
          canvas.width  = Math.ceil(rect.width * scale);
          canvas.height = Math.ceil(rect.height * scale);

          const ctx = canvas.getContext("2d");
          ctx.scale(scale, scale);
          ctx.fillStyle = "white";
          ctx.fillRect(0, 0, rect.width, rect.height);

          // Serialize the iframe body to SVG foreignObject
          const svgNS = "http://www.w3.org/2000/svg";
          const svg = document.createElementNS(svgNS, "svg");
          svg.setAttribute("width",  rect.width);
          svg.setAttribute("height", rect.height);

          const fo = document.createElementNS(svgNS, "foreignObject");
          fo.setAttribute("width",  "100%");
          fo.setAttribute("height", "100%");

          // Re-serialize body HTML for the foreignObject
          const div = document.createElement("div");
          div.setAttribute("xmlns", "http://www.w3.org/1999/xhtml");
          div.innerHTML = body.innerHTML;
          // Copy computed styles inline
          div.style.cssText = window.getComputedStyle(body).cssText;

          fo.appendChild(div);
          svg.appendChild(fo);

          const svgData = new XMLSerializer().serializeToString(svg);
          const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
          const url = URL.createObjectURL(svgBlob);

          const img = new Image();
          img.onload = () => {
            ctx.drawImage(img, 0, 0);
            URL.revokeObjectURL(url);
            document.body.removeChild(iframe);

            canvas.toBlob(blob => {
              if (blob) resolve(blob);
              else reject(new Error("Canvas toBlob failed"));
            }, "image/png");
          };
          img.onerror = () => {
            URL.revokeObjectURL(url);
            document.body.removeChild(iframe);
            reject(new Error("SVG image load failed"));
          };
          img.src = url;
        } catch (e) {
          document.body.removeChild(iframe);
          reject(e);
        }
      };

      iframe.contentDocument.open();
      iframe.contentDocument.write(htmlStr);
      iframe.contentDocument.close();
    });
  }

  /**
   * Build the ClipboardItem for the requested format.
   */
  function buildClipboardItem(format, containerElement) {
    // ── Google Docs (LaTeX for Auto-LaTeX add-on) ────────────────────────
    if (format === "google_docs") {
      const text = extractLaTeXText(containerElement);
      return new ClipboardItem({
        "text/plain": new Blob([text], { type: "text/plain" }),
      });
    }

    // ── Google Docs (raw LaTeX for Insert › Equation) ───────────────────
    if (format === "google_docs_eq") {
      const text = extractRawLaTeX(containerElement);
      return new ClipboardItem({
        "text/plain": new Blob([text], { type: "text/plain" }),
      });
    }

    // ── Word formats (MathML-based) ──────────────────────────────────────
    const { html, text } = extractMathML(containerElement);

    if (format === "word_legacy") {
      return new ClipboardItem({
        "text/html":  new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([html], { type: "text/plain" }),
      });
    }

    if (format === "word_web") {
      return new ClipboardItem({
        "text/html":  new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      });
    }

    // word_modern (default): MathML in minimal HTML document
    const wrapped =
      "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>" +
      html +
      "</body></html>";
    return new ClipboardItem({
      "text/html":  new Blob([wrapped], { type: "text/html" }),
      "text/plain": new Blob([text],    { type: "text/plain" }),
    });
  }

  // ── Core copy ────────────────────────────────────────────────────────────

  async function copyWithFormat(format, buttonElement, containerElement) {
    if (!containerElement) {
      console.error("copyMath: no container provided");
      return;
    }

    try {
      if (format === "google_docs_img") {
        // Image fallback: render to PNG and write to clipboard
        const blob = await renderToImageBlob(containerElement);
        await navigator.clipboard.write([
          new ClipboardItem({ "image/png": blob })
        ]);
      } else if (format === "google_docs") {
        // Google Docs LaTeX is pure plain text, use writeText for max browser compatibility
        const text = extractLaTeXText(containerElement);
        await navigator.clipboard.writeText(text);
    } else if (format === "google_docs_eq") {
        // Raw LaTeX for Insert › Equation — no $$ wrappers
        const text = extractRawLaTeX(containerElement);
        await navigator.clipboard.writeText(text);
      } else {
        const item = buildClipboardItem(format, containerElement);
        await navigator.clipboard.write([item]);
      }
      flashSuccess(buttonElement, format);
    } catch (err) {
      console.error("copyMath: failed to copy", err);

      // Graceful fallback: try plain-text raw LaTeX (no $$ delimiters)
      try {
        const fallbackText = extractRawLaTeX(containerElement);
        await navigator.clipboard.writeText(fallbackText);
        flashSuccess(buttonElement, format, true);
      } catch (e2) {
        alert("Copierea a eșuat. Asigură-te că ești pe HTTPS sau localhost.");
      }
    }
  }

  function flashSuccess(buttonElement, format, wasFallback) {
    if (!buttonElement) return;
    const original = buttonElement.innerHTML;

    const label = wasFallback ? "Copiat (text)" : "Copiat ✓";
    buttonElement.innerHTML =
      '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>' +
      '<span class="text-xs ml-1" style="color:#059669">' + label + '</span>';
    buttonElement.classList.add("bg-green-100", "border-green-200");
    setTimeout(() => {
      buttonElement.innerHTML = original;
      buttonElement.classList.remove("bg-green-100", "border-green-200");
    }, 2000);
  }

  // ── Public API ───────────────────────────────────────────────────────────

  window.copyMathToClipboard = function (buttonElement, containerElement) {
    const fmt = window._copyFormat || getFormat();
    window._copyFormat = null;   // consume once
    copyWithFormat(fmt, buttonElement, containerElement);
  };

  window.copyWithFormat = copyWithFormat;

  window.enhanceCopyButtons = function (root) {
    (root || document).querySelectorAll(".copy-math-btn").forEach(attachDropdown);
  };

  // ── Dropdown UI ──────────────────────────────────────────────────────────

  function attachDropdown(button) {
    if (button.dataset.copyEnhanced === "1") return;
    button.dataset.copyEnhanced = "1";

    // Walk up the DOM to find the nearest .msg-content-container.
    // Handles both old layout (sibling inside same parent) and new flex-header
    // layout (sibling of the header row, i.e. two levels up).
    function findContainer(el) {
      let node = el;
      for (let i = 0; i < 5; i++) {
        if (!node) break;
        const found = node.querySelector(".msg-content-container");
        if (found) return found;
        node = node.parentElement;
      }
      return el.parentElement || el;
    }
    const container = findContainer(button.parentElement);

    // Wrapper — flex-shrink:0 ensures it never collapses on narrow screens
    const wrap = document.createElement("div");
    wrap.className = "copy-format-wrap";
    wrap.style.cssText = "position:relative;display:inline-flex;align-items:stretch;flex-shrink:0;";
    button.replaceWith(wrap);

    // Main button copies with current format
    button.onclick = null;
    button.addEventListener("click", () =>
      copyWithFormat(getFormat(), button, container)
    );
    wrap.appendChild(button);

    // Caret toggle
    const caret = document.createElement("button");
    caret.type = "button";
    caret.className =
      "copy-format-caret text-slate-500 hover:text-slate-900 bg-slate-200 " +
      "hover:bg-slate-300 px-1 rounded-r-lg transition";
    caret.setAttribute("aria-label", "Alege formatul de copiere");
    caret.style.cssText = "margin-left:1px;border-top-left-radius:0;border-bottom-left-radius:0;";
    caret.innerHTML =
      '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"></path></svg>';
    wrap.appendChild(caret);

    // Menu panel — appended to <body> so overflow:hidden on ancestor containers
    // cannot clip it. Position is calculated via getBoundingClientRect on click.
    const menu = document.createElement("div");
    menu.className = "copy-format-menu";
    menu.style.cssText =
      "position:fixed;min-width:250px;z-index:9999;" +
      "background:#fff;border:1px solid #e2e8f0;border-radius:12px;" +
      "box-shadow:0 12px 32px rgba(15,23,42,.18);padding:6px;display:none;" +
      "max-height:320px;overflow-y:auto;";
    document.body.appendChild(menu);

    function renderMenu() {
      const current = getFormat();
      menu.innerHTML = "";

      // Section header for Word
      addSectionHeader(menu, "Microsoft Word");

      FORMATS.filter(f => f.id.startsWith("word")).forEach(f => {
        menu.appendChild(createOption(f, current, button, container, menu));
      });

      // Divider
      const hr = document.createElement("div");
      hr.style.cssText = "height:1px;background:#e2e8f0;margin:6px 8px;";
      menu.appendChild(hr);

      // Section header for Google Docs
      addSectionHeader(menu, "Google Docs");

      FORMATS.filter(f => f.id.startsWith("google")).forEach(f => {
        menu.appendChild(createOption(f, current, button, container, menu));
      });
    }

    caret.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = menu.style.display === "block";
      // Close all other open menus
      document.querySelectorAll(".copy-format-menu").forEach(m => (m.style.display = "none"));
      if (!isOpen) {
        renderMenu();
        // Position the fixed menu relative to the caret button in the viewport
        const rect = caret.getBoundingClientRect();
        menu.style.top  = (rect.bottom + 6) + "px";
        menu.style.left = "auto";
        menu.style.right = (window.innerWidth - rect.right) + "px";
        menu.style.display = "block";
      }
    });

    document.addEventListener("click", () => { menu.style.display = "none"; });
  }

  function addSectionHeader(menu, text) {
    const header = document.createElement("div");
    header.textContent = text;
    header.style.cssText =
      "padding:6px 10px 4px;font-size:10px;font-weight:700;text-transform:uppercase;" +
      "letter-spacing:0.08em;color:#94a3b8;user-select:none;";
    menu.appendChild(header);
  }

  function createOption(f, current, button, container, menu) {
    const opt = document.createElement("button");
    opt.type = "button";
    const active = f.id === current;
    opt.innerHTML =
      '<span style="font-size:15px;margin-right:8px;">' + f.icon + '</span>' +
      '<span><strong style="font-size:13px;display:block;line-height:1.3;">' + f.label + '</strong>' +
      '<span style="font-size:11px;color:#64748b;">' + f.desc + '</span></span>';
    opt.style.cssText =
      "display:flex;align-items:center;width:100%;text-align:left;padding:8px 10px;border:none;" +
      "background:" + (active ? "#ecfeff" : "transparent") + ";" +
      "color:#0f172a;border-radius:8px;cursor:pointer;transition:background .15s;" +
      (active ? "box-shadow:inset 0 0 0 1.5px #06b6d4;" : "");
    opt.addEventListener("mouseenter", () => { if (!active) opt.style.background = "#f1f5f9"; });
    opt.addEventListener("mouseleave", () => { if (!active) opt.style.background = active ? "#ecfeff" : "transparent"; });
    opt.addEventListener("click", (e) => {
      e.stopPropagation();
      setFormat(f.id);
      menu.style.display = "none";
      copyWithFormat(f.id, button, container);
    });
    return opt;
  }

  // ── Auto-init ────────────────────────────────────────────────────────────

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () =>
      setTimeout(() => window.enhanceCopyButtons(), 0)
    );
  } else {
    setTimeout(() => window.enhanceCopyButtons(), 0);
  }
})();
