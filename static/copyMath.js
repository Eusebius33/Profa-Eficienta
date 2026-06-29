// copyMath.js
// Format-aware "Copiaza" button for KaTeX-rendered math.
// Drop-in replacement: the old copyMathToClipboard(btn, container) signature
// still works (it now copies using the user's last-selected format).
//
// Four formats, matching the design mockup. Each one targets a different
// paste destination, because no single clipboard payload pastes cleanly
// into every editor:
//
//   word_legacy  -> "Word <2011"   : MathML only. Old Word builds choke when
//                                     HTML presentation markup is also present,
//                                     so we send a bare <math> element.
//   word_modern  -> "Word >2011"   : MathML wrapped in minimal HTML. Modern
//                                     desktop Word converts this to native OMML.
//   word_web     -> "Word web"     : MathML + a plain-text LaTeX fallback. The
//                                     browser version of Word is pickier; the
//                                     text fallback keeps something useful if
//                                     the equation import fails.
//   google_docs  -> "Google docs"  : Plain Unicode/text. Google Docs does NOT
//                                     import MathML; it only reliably accepts
//                                     plain text, so we paste a readable
//                                     Unicode-ish rendering of the expression.
//
// HONEST LIMITATION: Word and Google Docs re-render math in their own equation
// engines with their own fonts. Output is correct, editable and printable, but
// it will NOT be pixel-identical to the KaTeX rendering on the website. That is
// a platform constraint, not a bug in this file.

(function () {
  const STORAGE_KEY = "copiaza_format";
  const DEFAULT_FORMAT = "word_legacy"; // mockup marks Word <2011 as default

  const FORMATS = [
    { id: "word_legacy", label: "Word <2011" },
    { id: "word_modern", label: "Word >2011" },
    { id: "word_web",    label: "Word web" },
    { id: "google_docs", label: "Google docs" },
  ];

  function getFormat() {
    try {
      return localStorage.getItem(STORAGE_KEY) || DEFAULT_FORMAT;
    } catch (e) {
      return DEFAULT_FORMAT;
    }
  }

  function setFormat(id) {
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch (e) { /* private mode etc. – ignore */ }
  }

  // ---- payload builders ---------------------------------------------------

  // Clone the math container and strip KaTeX's visual HTML so only MathML stays.
  function extractMathML(containerElement) {
    const clone = containerElement.cloneNode(true);

    clone.querySelectorAll(".copy-math-btn, .copy-format-wrap").forEach(el => el.remove());

    clone.querySelectorAll("math").forEach(mathEl => {
      mathEl.setAttribute("xmlns", "http://www.w3.org/1998/Math/MathML");
      if (!mathEl.hasAttribute("display")) mathEl.setAttribute("display", "inline");
    });

    // KaTeX puts MathML in .katex-mathml and the visual HTML in .katex-html.
    // Removing .katex-html leaves clean MathML for Word to import.
    clone.querySelectorAll(".katex-html").forEach(el => el.remove());

    return { html: clone.innerHTML, text: clone.innerText };
  }

  // Best-effort plain-text rendering for Google Docs (which ignores MathML).
  function extractPlainText(containerElement) {
    const clone = containerElement.cloneNode(true);
    clone.querySelectorAll(".copy-math-btn, .copy-format-wrap").forEach(el => el.remove());
    // innerText of the KaTeX HTML already contains Unicode symbols (√, ∫, ², …)
    return clone.innerText.replace(/\u00a0/g, " ").replace(/[ \t]+\n/g, "\n").trim();
  }

  function buildClipboardItem(format, containerElement) {
    if (format === "google_docs") {
      const text = extractPlainText(containerElement);
      return new ClipboardItem({
        "text/plain": new Blob([text], { type: "text/plain" }),
      });
    }

    const { html, text } = extractMathML(containerElement);

    if (format === "word_legacy") {
      // MathML only, mirrored into text/plain. No surrounding HTML wrapper.
      return new ClipboardItem({
        "text/html":  new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([html], { type: "text/plain" }),
      });
    }

    if (format === "word_web") {
      // MathML for the equation, LaTeX-ish text as a graceful fallback.
      return new ClipboardItem({
        "text/html":  new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      });
    }

    // word_modern (default for modern desktop Word): MathML in a minimal
    // HTML document, which desktop Word converts to native equations.
    const wrapped =
      "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>" +
      html +
      "</body></html>";
    return new ClipboardItem({
      "text/html":  new Blob([wrapped], { type: "text/html" }),
      "text/plain": new Blob([text], { type: "text/plain" }),
    });
  }

  // ---- core copy ----------------------------------------------------------

  async function copyWithFormat(format, buttonElement, containerElement) {
    if (!containerElement) {
      console.error("copyMath: no container provided");
      return;
    }
    try {
      const item = buildClipboardItem(format, containerElement);
      await navigator.clipboard.write([item]);
      flashSuccess(buttonElement);
    } catch (err) {
      console.error("copyMath: failed to copy", err);
      alert("Copierea a esuat. Asigura-te ca esti pe HTTPS sau localhost.");
    }
  }

  function flashSuccess(buttonElement) {
    if (!buttonElement) return;
    const original = buttonElement.innerHTML;
    buttonElement.innerHTML =
      '<svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
    buttonElement.classList.add("bg-green-100", "border-green-200");
    setTimeout(() => {
      buttonElement.innerHTML = original;
      buttonElement.classList.remove("bg-green-100", "border-green-200");
    }, 2000);
  }

  // ---- public: backwards-compatible entry point ---------------------------
  // Existing templates call this with (this, container). It now copies using
  // whatever format the user last selected.
  window.copyMathToClipboard = function (buttonElement, containerElement) {
    copyWithFormat(getFormat(), buttonElement, containerElement);
  };

  // ---- public: dropdown wiring -------------------------------------------
  // Call enhanceCopyButtons() after the page (and KaTeX) have rendered. It
  // finds every .copy-math-btn and attaches a format-picker dropdown next to it.
  window.enhanceCopyButtons = function (root) {
    (root || document).querySelectorAll(".copy-math-btn").forEach(attachDropdown);
  };

  function attachDropdown(button) {
    if (button.dataset.copyEnhanced === "1") return;
    button.dataset.copyEnhanced = "1";

    const container =
      button.closest(".group")?.querySelector(".msg-content-container") ||
      button.parentElement.querySelector(".msg-content-container") ||
      button.parentElement;

    // Wrapper so the menu can be positioned relative to the button.
    const wrap = document.createElement("div");
    wrap.className = "copy-format-wrap";
    wrap.style.cssText = "position:relative;display:inline-flex;align-items:stretch;";
    button.replaceWith(wrap);

    // Main copy action uses the saved format.
    button.onclick = null;
    button.addEventListener("click", () =>
      copyWithFormat(getFormat(), button, container)
    );
    wrap.appendChild(button);

    // Caret that opens the format list.
    const caret = document.createElement("button");
    caret.type = "button";
    caret.className =
      "copy-format-caret text-slate-500 hover:text-slate-900 bg-slate-200 hover:bg-slate-300 px-1 rounded-lg transition";
    caret.setAttribute("aria-label", "Alege formatul de copiere");
    caret.style.cssText = "margin-left:2px;";
    caret.innerHTML =
      '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>';
    wrap.appendChild(caret);

    // The menu.
    const menu = document.createElement("div");
    menu.className = "copy-format-menu";
    menu.style.cssText =
      "position:absolute;top:100%;right:0;margin-top:4px;min-width:170px;z-index:50;" +
      "background:#fff;border:1px solid #e2e8f0;border-radius:10px;" +
      "box-shadow:0 8px 24px rgba(15,23,42,.15);padding:4px;display:none;";

    function renderMenu() {
      const current = getFormat();
      menu.innerHTML = "";
      FORMATS.forEach(f => {
        const opt = document.createElement("button");
        opt.type = "button";
        opt.textContent = "Copiaza format " + f.label;
        const active = f.id === current;
        opt.style.cssText =
          "display:block;width:100%;text-align:left;padding:7px 10px;border:none;" +
          "background:" + (active ? "#ecfeff" : "transparent") + ";" +
          "color:#0f172a;font-size:13px;border-radius:7px;cursor:pointer;" +
          (active ? "font-weight:600;" : "");
        opt.addEventListener("mouseenter", () => { if (!active) opt.style.background = "#f1f5f9"; });
        opt.addEventListener("mouseleave", () => { if (!active) opt.style.background = "transparent"; });
        opt.addEventListener("click", () => {
          setFormat(f.id);          // persisted across all modes
          menu.style.display = "none";
          copyWithFormat(f.id, button, container); // copy immediately on pick
        });
        menu.appendChild(opt);
      });
    }

    caret.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = menu.style.display === "block";
      document.querySelectorAll(".copy-format-menu").forEach(m => (m.style.display = "none"));
      if (!open) { renderMenu(); menu.style.display = "block"; }
    });

    document.addEventListener("click", () => { menu.style.display = "none"; });
    wrap.appendChild(menu);
  }

  // Auto-enhance once everything (KaTeX auto-render) has settled.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () =>
      setTimeout(() => window.enhanceCopyButtons(), 0)
    );
  } else {
    setTimeout(() => window.enhanceCopyButtons(), 0);
  }
})();
