// editor.js — Document Editor: equation ribbon, text formatting, file actions,
// document history and the 5-mode AI panel.
(function () {
    "use strict";

    const shell = document.querySelector(".ed-shell");
    if (!shell) return;

    const documentId = shell.dataset.documentId;
    const docBody = document.getElementById("docBody");

    // server-rendered data lives in data-* attributes (not an inline <script>
    // with template syntax) so it's just an opaque string to any HTML/JS
    // tooling and never gets mis-parsed as JavaScript
    const editorDataEl = document.getElementById("edEditorData");
    function readEditorData(key, fallback) {
        if (!editorDataEl) return fallback;
        try { return JSON.parse(editorDataEl.dataset[key]); } catch (e) { return fallback; }
    }
    const MODES = readEditorData("modes", []);
    const EDITOR_I18N = readEditorData("i18n", {});
    const MODE_BY_KEY = {};
    MODES.forEach(m => { MODE_BY_KEY[m.key] = m; });

    // =====================================================
    // TOAST
    // =====================================================
    let toastTimer = null;
    function toast(msg, isError) {
        const el = document.getElementById("edToast");
        if (!el) return;
        el.textContent = msg;
        el.classList.remove("hidden");
        el.classList.toggle("ed-toast-error", !!isError);
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => el.classList.add("hidden"), 3200);
    }

    // =====================================================
    // MATH RENDERING
    // =====================================================
    function renderMathIn(el) {
        if (!el || typeof window.renderMathInElement !== "function") return;
        // populate visible text from data-math for freshly-inserted nodes
        el.querySelectorAll(".math-content[data-math]").forEach(node => {
            if (!node.dataset.rendered) {
                node.textContent = node.dataset.math;
            }
        });
        try {
            window.renderMathInElement(el, {
                delimiters: [
                    { left: "$$", right: "$$", display: true },
                    { left: "$", right: "$", display: false }
                ],
                throwOnError: false
            });
        } catch (e) { /* ignore */ }
        el.querySelectorAll(".math-content[data-math]").forEach(node => { node.dataset.rendered = "1"; });
    }
    renderMathIn(docBody);
    renderMathIn(document.getElementById("edAiPanelBody"));

    // =====================================================
    // RIBBON TABS
    // =====================================================
    const tabButtons = document.querySelectorAll(".ed-ribbon-tab[data-tab]");
    const ribbonHome = document.getElementById("ed-ribbon-home");
    const ribbonEquation = document.getElementById("ed-ribbon-equation");

    function showTab(tab) {
        tabButtons.forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
        ribbonHome.style.display = tab === "home" ? "flex" : "none";
        ribbonEquation.style.display = tab === "equation" ? "flex" : "none";
    }
    tabButtons.forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));

    // =====================================================
    // EQUATION BOX ENGINE
    // =====================================================
    let activeEqBox = null;
    let eqDisplayMode = "latex"; // "latex" | "unicode"
    // guards the selectionchange listener while we programmatically move
    // focus/caret — docBody.focus() on an emptied box can synchronously fire
    // a transient selectionchange (browser's default caret placement)
    // *before* we place the real caret, which would otherwise be mistaken
    // for "the user left the equation box" and wipe it out.
    let suppressSelectionSync = false;

    const UNICODE_MAP = [
        [/\\pm/g, "±"], [/\\mp/g, "∓"], [/\\times/g, "×"], [/\\div/g, "÷"],
        [/\\leq/g, "≤"], [/\\geq/g, "≥"], [/\\neq/g, "≠"], [/\\approx/g, "≈"],
        [/\\equiv/g, "≡"], [/\\infty/g, "∞"], [/\\partial/g, "∂"], [/\\cdot/g, "·"],
        [/\\alpha/g, "α"], [/\\beta/g, "β"], [/\\gamma/g, "γ"], [/\\delta/g, "δ"],
        [/\\epsilon/g, "ε"], [/\\theta/g, "θ"], [/\\lambda/g, "λ"], [/\\mu/g, "μ"],
        [/\\pi/g, "π"], [/\\sigma/g, "σ"], [/\\phi/g, "φ"], [/\\omega/g, "ω"],
        [/\\sum/g, "Σ"], [/\\int/g, "∫"], [/\\sqrt\{([^}]*)\}/g, "√($1)"],
        [/\\frac\{([^}]*)\}\{([^}]*)\}/g, "($1)⁄($2)"],
        [/\^\{([^}]*)\}/g, "^($1)"], [/_\{([^}]*)\}/g, "_($1)"],
        [/[{}]/g, ""]
    ];
    function latexToUnicodeApprox(latex) {
        let out = latex || "";
        UNICODE_MAP.forEach(([re, rep]) => { out = out.replace(re, rep); });
        return out;
    }

    // NOTE: eq-box elements are plain (non-focusable) spans that inherit
    // editability from the single contenteditable host (#docBody). Nested
    // contenteditable elements do NOT become document.activeElement in
    // browsers, so "editing state" is tracked via caret position
    // (selectionchange) rather than focus/blur on the box itself.
    function placeCaretInNode(el, atEnd) {
        const range = document.createRange();
        range.selectNodeContents(el);
        range.collapse(!atEnd);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }

    function renderEqPreview(box) {
        const latex = box.dataset.latex || "";
        box.classList.remove("eq-editing");
        box.classList.add("eq-rendered");
        if (!latex.trim()) {
            box.innerHTML = '<span class="eq-placeholder">≡</span>';
            return;
        }
        if (eqDisplayMode === "unicode") {
            box.textContent = latexToUnicodeApprox(latex);
            return;
        }
        if (typeof window.katex !== "undefined") {
            try {
                window.katex.render(latex, box, { throwOnError: false, output: "html" });
                return;
            } catch (e) { /* fall through */ }
        }
        box.textContent = latex;
    }

    function enterEqEdit(box) {
        if (activeEqBox && activeEqBox !== box) exitEqEdit(activeEqBox);
        suppressSelectionSync = true;
        box.classList.remove("eq-rendered");
        box.classList.add("eq-editing");
        box.textContent = box.dataset.latex || "";
        activeEqBox = box;
        docBody.focus();
        placeCaretInNode(box, true);
        suppressSelectionSync = false;
    }

    function exitEqEdit(box) {
        if (!box) return;
        box.dataset.latex = box.textContent.trim();
        renderEqPreview(box);
        if (activeEqBox === box) activeEqBox = null;
    }

    function insertEquationBox(initialLatex) {
        const box = document.createElement("span");
        box.className = "eq-box";
        box.dataset.latex = initialLatex || "";

        const sel = window.getSelection();
        if (sel && sel.rangeCount && docBody.contains(sel.anchorNode)) {
            const range = sel.getRangeAt(0);
            range.deleteContents();
            range.insertNode(box);
            range.setStartAfter(box);
            range.collapse(true);
            sel.removeAllRanges();
            sel.addRange(range);
        } else {
            docBody.appendChild(box);
        }
        docBody.appendChild(document.createTextNode(" "));
        renderEqPreview(box);
        enterEqEdit(box);
        return box;
    }

    function wireEqBox(box) {
        // used for equation boxes already present in saved document content
        renderEqPreview(box);
    }

    docBody.querySelectorAll(".eq-box").forEach(wireEqBox);

    // track caret entering/leaving an eq-box to switch it between
    // raw-LaTeX-editing and rendered-preview states
    document.addEventListener("selectionchange", () => {
        if (suppressSelectionSync) return;
        if (document.activeElement !== docBody) return;
        const sel = window.getSelection();
        if (!sel.rangeCount) return;
        const node = sel.anchorNode;
        const el = node && (node.nodeType === 3 ? node.parentElement : node);
        const box = el && el.closest ? el.closest(".eq-box") : null;

        if (box === activeEqBox) return;
        if (activeEqBox) exitEqEdit(activeEqBox);
        if (box && !box.classList.contains("eq-editing")) {
            suppressSelectionSync = true;
            box.classList.remove("eq-rendered");
            box.classList.add("eq-editing");
            box.textContent = box.dataset.latex || "";
            activeEqBox = box;
            placeCaretInNode(box, true);
            suppressSelectionSync = false;
        }
    });

    // selectionchange only fires while the caret moves *within* docBody; if
    // focus leaves docBody entirely (ribbon button, title field, AI panel
    // input...) the active equation must still be committed and re-rendered.
    docBody.addEventListener("blur", () => {
        if (activeEqBox) exitEqEdit(activeEqBox);
    });

    // Enter exits the active equation instead of inserting a newline inside it
    docBody.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && activeEqBox) {
            e.preventDefault();
            const box = activeEqBox;
            suppressSelectionSync = true;
            exitEqEdit(box);
            const range = document.createRange();
            range.setStartAfter(box);
            range.collapse(true);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            suppressSelectionSync = false;
        }
    });

    function insertTextAtCaretInBox(box, text, caretBackFromEnd) {
        docBody.focus();
        if (activeEqBox !== box || !box.classList.contains("eq-editing")) {
            enterEqEdit(box);
        } else {
            suppressSelectionSync = true;
            placeCaretInNode(box, true);
            suppressSelectionSync = false;
        }
        const sel = window.getSelection();
        const range = sel.getRangeAt(0);
        range.deleteContents();
        const node = document.createTextNode(text);
        range.insertNode(node);
        range.setStartAfter(node);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
        for (let i = 0; i < (caretBackFromEnd || 0); i++) sel.modify("move", "backward", "character");
    }

    function insertLatexSnippet(latex, caretBack) {
        let box = activeEqBox;
        if (!box || !document.body.contains(box)) {
            box = insertEquationBox("");
        }
        insertTextAtCaretInBox(box, latex, caretBack || 0);
    }

    document.getElementById("edInsertEquation").addEventListener("click", () => insertEquationBox(""));
    document.getElementById("edInsertEquationHome").addEventListener("click", () => {
        showTab("equation");
        insertEquationBox("");
    });

    document.querySelectorAll(".ed-sym-btn").forEach(btn => {
        btn.addEventListener("click", () => insertLatexSnippet(btn.dataset.insert, 0));
    });

    // =====================================================
    // FAVORITE SYMBOLS (localStorage, right-click any symbol to toggle)
    // =====================================================
    const I18N = EDITOR_I18N;
    const FAV_STORAGE_KEY = "ed_favorite_symbols";
    const favoritesRow = document.getElementById("edFavoritesRow");
    const favoritesEmpty = document.getElementById("edFavoritesEmpty");

    function loadFavorites() {
        try {
            const arr = JSON.parse(localStorage.getItem(FAV_STORAGE_KEY) || "[]");
            return Array.isArray(arr) ? arr : [];
        } catch (e) { return []; }
    }
    function saveFavorites(arr) {
        try { localStorage.setItem(FAV_STORAGE_KEY, JSON.stringify(arr)); } catch (e) { /* storage unavailable */ }
    }
    function renderFavorites() {
        if (!favoritesRow) return;
        const favs = loadFavorites();
        favoritesRow.querySelectorAll(".ed-fav-btn").forEach(b => b.remove());
        if (favoritesEmpty) favoritesEmpty.style.display = favs.length ? "none" : "block";
        favs.forEach(f => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "ed-fav-btn";
            btn.dataset.insert = f.latex;
            btn.title = f.latex;
            btn.textContent = f.sym;
            favoritesRow.appendChild(btn);
        });
    }
    function toggleFavorite(sym, latex) {
        if (!latex) return;
        const favs = loadFavorites();
        const idx = favs.findIndex(f => f.latex === latex);
        if (idx >= 0) {
            favs.splice(idx, 1);
            saveFavorites(favs);
            toast(I18N.favoriteRemoved || "Eliminat din favorite");
        } else {
            favs.push({ sym, latex });
            saveFavorites(favs);
            toast(I18N.favoriteAdded || "Adăugat la favorite");
        }
        renderFavorites();
    }
    renderFavorites();

    if (favoritesRow) {
        favoritesRow.addEventListener("click", (e) => {
            const btn = e.target.closest(".ed-fav-btn");
            if (btn) insertLatexSnippet(btn.dataset.insert, 0);
        });
    }
    // right-click any symbol (main grid, "more symbols" grid, or a favorite
    // itself) to add/remove it from favorites, instead of the native menu
    document.addEventListener("contextmenu", (e) => {
        const btn = e.target.closest(".ed-sym-btn, .ed-fav-btn");
        if (!btn) return;
        e.preventDefault();
        toggleFavorite(btn.textContent.trim(), btn.dataset.insert);
    });

    document.querySelectorAll(".ed-struct-menu .ed-dropdown-item").forEach(btn => {
        btn.addEventListener("click", () => {
            insertLatexSnippet(btn.dataset.insert, parseInt(btn.dataset.caretback || "0", 10));
            closeAllDropdowns();
        });
    });

    function setEqDisplayMode(mode) {
        eqDisplayMode = mode;
        document.querySelectorAll(".ed-toggle-btn[data-eqmode]").forEach(b => {
            b.classList.toggle("active", b.dataset.eqmode === mode);
        });
        docBody.querySelectorAll(".eq-box.eq-rendered").forEach(renderEqPreview);
        closeAllDropdowns();
    }
    document.querySelectorAll("[data-eqmode]").forEach(btn => {
        btn.addEventListener("click", () => setEqDisplayMode(btn.dataset.eqmode));
    });

    // dropdowns (Convert ▾ / More symbols ▾ / structure menus)
    // menus are positioned via fixed coordinates (computed on open) rather
    // than being absolutely positioned inside .ed-ribbon, which clips
    // overflow because of its horizontal scrollbar (overflow-x: auto forces
    // overflow-y: auto too, per the CSS overflow spec).
    function closeAllDropdowns() {
        document.querySelectorAll(".ed-dropdown.open").forEach(d => d.classList.remove("open"));
    }
    document.querySelectorAll(".ed-dropdown-toggle").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const dd = btn.closest(".ed-dropdown");
            const wasOpen = dd.classList.contains("open");
            closeAllDropdowns();
            if (!wasOpen) {
                dd.classList.add("open");
                const menu = dd.querySelector(".ed-dropdown-menu");
                const rect = btn.getBoundingClientRect();
                menu.style.position = "fixed";
                menu.style.top = (rect.bottom + 4) + "px";
                menu.style.left = rect.left + "px";
            }
        });
    });
    document.addEventListener("click", closeAllDropdowns);

    // =====================================================
    // INK EQUATION — freehand canvas drawing, inserted as an inline image
    // at the caret position that was active when the modal was opened
    // =====================================================
    const inkOverlay = document.getElementById("edInkOverlay");
    const inkCanvas = document.getElementById("edInkCanvas");
    const inkCtx = inkCanvas ? inkCanvas.getContext("2d") : null;
    let inkStrokes = [];
    let inkDrawing = false;
    let inkSavedRange = null;

    function resizeInkCanvas() {
        if (!inkCanvas || !inkCtx) return;
        const rect = inkCanvas.getBoundingClientRect();
        const ratio = window.devicePixelRatio || 1;
        inkCanvas.width = rect.width * ratio;
        inkCanvas.height = rect.height * ratio;
        inkCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
        redrawInk();
    }

    function redrawInk() {
        if (!inkCtx || !inkCanvas) return;
        const rect = inkCanvas.getBoundingClientRect();
        inkCtx.clearRect(0, 0, rect.width, rect.height);
        inkCtx.lineCap = "round";
        inkCtx.lineJoin = "round";
        inkCtx.lineWidth = 2.5;
        inkCtx.strokeStyle = "#0f172a";
        inkStrokes.forEach(stroke => {
            if (stroke.length < 2) return;
            inkCtx.beginPath();
            inkCtx.moveTo(stroke[0].x, stroke[0].y);
            for (let i = 1; i < stroke.length; i++) inkCtx.lineTo(stroke[i].x, stroke[i].y);
            inkCtx.stroke();
        });
    }

    function inkPointFromEvent(e) {
        const rect = inkCanvas.getBoundingClientRect();
        return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    if (inkCanvas) {
        inkCanvas.addEventListener("pointerdown", (e) => {
            inkDrawing = true;
            inkCanvas.setPointerCapture(e.pointerId);
            inkStrokes.push([inkPointFromEvent(e)]);
        });
        inkCanvas.addEventListener("pointermove", (e) => {
            if (!inkDrawing) return;
            inkStrokes[inkStrokes.length - 1].push(inkPointFromEvent(e));
            redrawInk();
        });
        const endInkStroke = () => { inkDrawing = false; };
        inkCanvas.addEventListener("pointerup", endInkStroke);
        inkCanvas.addEventListener("pointercancel", endInkStroke);
        inkCanvas.addEventListener("pointerleave", () => { if (inkDrawing) endInkStroke(); });
    }

    function openInkModal() {
        const sel = window.getSelection();
        inkSavedRange = (sel && sel.rangeCount && docBody.contains(sel.anchorNode))
            ? sel.getRangeAt(0).cloneRange() : null;
        inkStrokes = [];
        inkOverlay.classList.remove("hidden");
        requestAnimationFrame(resizeInkCanvas);
    }
    function closeInkModal() {
        inkOverlay.classList.add("hidden");
    }

    const inkEquationBtn = document.getElementById("edInkEquation");
    if (inkEquationBtn) inkEquationBtn.addEventListener("click", openInkModal);

    const edInkCloseBtn = document.getElementById("edInkCloseBtn");
    if (edInkCloseBtn) edInkCloseBtn.addEventListener("click", closeInkModal);
    const edInkCancelBtn = document.getElementById("edInkCancelBtn");
    if (edInkCancelBtn) edInkCancelBtn.addEventListener("click", closeInkModal);
    const edInkClearBtn = document.getElementById("edInkClearBtn");
    if (edInkClearBtn) edInkClearBtn.addEventListener("click", () => { inkStrokes = []; redrawInk(); });
    const edInkUndoBtn = document.getElementById("edInkUndoBtn");
    if (edInkUndoBtn) edInkUndoBtn.addEventListener("click", () => { inkStrokes.pop(); redrawInk(); });

    const edInkInsertBtn = document.getElementById("edInkInsertBtn");
    if (edInkInsertBtn) {
        const inkInsertLabel = edInkInsertBtn.textContent;
        edInkInsertBtn.addEventListener("click", () => {
            if (!inkStrokes.length || edInkInsertBtn.disabled) { if (!inkStrokes.length) closeInkModal(); return; }
            const dataUrl = inkCanvas.toDataURL("image/png");

            edInkInsertBtn.disabled = true;
            edInkInsertBtn.textContent = "…";
            inkOverlay.classList.add("ed-ink-processing");

            // ink equations are OCR'd through the same handwriting-transcription
            // pipeline mode4 uses, so they land in the document as real,
            // KaTeX-rendered equations rather than a static picture of ink
            fetch(`/editor/${documentId}/ink-transcribe`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: dataUrl })
            })
                .then(r => r.json())
                .then(data => {
                    edInkInsertBtn.disabled = false;
                    edInkInsertBtn.textContent = inkInsertLabel;
                    inkOverlay.classList.remove("ed-ink-processing");

                    if (!data.ok || !data.latex_blocks || !data.latex_blocks.length) {
                        toast(
                            data.error === "empty_transcription"
                                ? "Nu am putut recunoaște nicio ecuație în desen"
                                : "Eroare la transcriere",
                            true
                        );
                        return;
                    }

                    docBody.focus();
                    const sel = window.getSelection();
                    if (inkSavedRange) {
                        sel.removeAllRanges();
                        sel.addRange(inkSavedRange);
                    }
                    data.latex_blocks.forEach(latex => {
                        const box = insertEquationBox(latex);
                        exitEqEdit(box);
                    });
                    scheduleAutosave();
                    toast(I18N.insertedToDoc || "Adăugat în document");
                    closeInkModal();
                })
                .catch(() => {
                    edInkInsertBtn.disabled = false;
                    edInkInsertBtn.textContent = inkInsertLabel;
                    inkOverlay.classList.remove("ed-ink-processing");
                    toast("Eroare de rețea", true);
                });
        });
    }

    window.addEventListener("resize", () => {
        if (inkOverlay && !inkOverlay.classList.contains("hidden")) resizeInkCanvas();
    });

    // =====================================================
    // HOME RIBBON — TEXT FORMATTING
    // =====================================================
    docBody.addEventListener("mousedown", () => { /* keep selection for exec commands */ });

    document.querySelectorAll("#ed-ribbon-home [data-cmd]").forEach(btn => {
        btn.addEventListener("click", () => {
            docBody.focus();
            document.execCommand(btn.dataset.cmd, false, null);
            scheduleAutosave();
        });
    });

    document.getElementById("edFontFamily").addEventListener("change", function () {
        docBody.focus();
        document.execCommand("fontName", false, this.value);
        scheduleAutosave();
    });
    document.getElementById("edFontSize").addEventListener("change", function () {
        docBody.focus();
        document.execCommand("fontSize", false, this.value);
        scheduleAutosave();
    });
    document.getElementById("edHeading").addEventListener("change", function () {
        docBody.focus();
        document.execCommand("formatBlock", false, this.value);
        scheduleAutosave();
    });
    document.getElementById("edTextColor").addEventListener("input", function () {
        docBody.focus();
        document.execCommand("foreColor", false, this.value);
        scheduleAutosave();
    });
    document.getElementById("edHighlightColor").addEventListener("input", function () {
        docBody.focus();
        document.execCommand("hiliteColor", false, this.value);
        scheduleAutosave();
    });

    // =====================================================
    // SAVE / AUTOSAVE
    // =====================================================
    const saveStatusEl = document.getElementById("edSaveStatus");
    let saveTimer = null;

    function saveNow() {
        saveStatusEl.textContent = "Se salvează...";
        return fetch(`/editor/${documentId}/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: docBody.innerHTML })
        }).then(r => r.json()).then(data => {
            saveStatusEl.textContent = data.ok ? "Salvat" : "Eroare la salvare";
        }).catch(() => { saveStatusEl.textContent = "Eroare la salvare"; });
    }

    function scheduleAutosave() {
        saveStatusEl.textContent = "Modificări nesalvate...";
        clearTimeout(saveTimer);
        saveTimer = setTimeout(saveNow, 1200);
    }

    docBody.addEventListener("input", scheduleAutosave);
    document.getElementById("edSaveBtn").addEventListener("click", saveNow);

    window.addEventListener("beforeunload", () => {
        navigator.sendBeacon && navigator.sendBeacon(
            `/editor/${documentId}/save`,
            new Blob([JSON.stringify({ content: docBody.innerHTML })], { type: "application/json" })
        );
    });

    // =====================================================
    // TITLE RENAME
    // =====================================================
    const titleInput = document.getElementById("edTitleInput");
    let lastTitle = titleInput.value;
    function commitTitle() {
        const value = titleInput.value.trim();
        if (!value || value === lastTitle) { titleInput.value = lastTitle; return; }
        const fd = new FormData();
        fd.append("new_title", value);
        fetch(`/editor/${documentId}/rename`, { method: "POST", body: fd }).then(() => {
            lastTitle = value;
            toast("Titlu actualizat");
        });
    }
    titleInput.addEventListener("blur", commitTitle);
    titleInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); titleInput.blur(); } });

    // =====================================================
    // OPEN / PRINT / DOWNLOAD
    // =====================================================
    document.getElementById("edOpenBtn").addEventListener("click", () => document.getElementById("edOpenInput").click());
    document.getElementById("edOpenInput").addEventListener("change", function () {
        const file = this.files[0];
        if (!file) return;
        const fd = new FormData();
        fd.append("file", file);
        toast("Se încarcă fișierul...");
        fetch(`/editor/${documentId}/open`, { method: "POST", body: fd })
            .then(r => r.json())
            .then(data => {
                if (!data.ok) { toast(data.error || "Eroare la deschidere", true); return; }
                docBody.insertAdjacentHTML("beforeend", `<div class="ed-open-divider">— ${data.filename} —</div>` + data.html);
                docBody.querySelectorAll(".eq-box").forEach(wireEqBox);
                renderMathIn(docBody);
                scheduleAutosave();
                toast("Fișier adăugat în document");
            })
            .catch(() => toast("Eroare la deschidere", true));
        this.value = "";
    });

    document.getElementById("edPrintBtn").addEventListener("click", () => {
        saveNow().then(() => window.open(`/editor/${documentId}/print`, "_blank"));
    });

    document.querySelector('a[href$="/download"]').addEventListener("click", function (e) {
        e.preventDefault();
        const href = this.href;
        saveNow().then(() => { window.location.href = href; });
    });

    // =====================================================
    // DOCUMENT HISTORY SIDEBAR
    // =====================================================
    window.toggleDocMenu = function (event, docId) {
        event.preventDefault();
        event.stopPropagation();
        document.querySelectorAll("[id^='doc-menu-']").forEach(m => {
            if (m.id !== "doc-menu-" + docId) m.classList.add("hidden");
        });
        const menu = document.getElementById("doc-menu-" + docId);
        if (menu) menu.classList.toggle("hidden");
    };
    document.addEventListener("click", () => {
        document.querySelectorAll("[id^='doc-menu-']").forEach(m => m.classList.add("hidden"));
    });
    window.prepareRenameDoc = function (form) {
        const current = form.dataset.title || "";
        const value = prompt("Titlul documentului:", current);
        if (value === null) return false;
        if (!value.trim()) { alert("Titlul nu poate fi gol."); return false; }
        form.querySelector("input[name='new_title']").value = value.trim();
        return true;
    };

    // =====================================================
    // AI BLOCKS IN DOCUMENT
    // =====================================================
    window.removeAiBlock = function (btn) {
        const block = btn.closest(".ai-block");
        if (block) {
            block.remove();
            scheduleAutosave();
        }
    };

    // =====================================================
    // MODE START-FORM INPUTS — auto-grow textareas, drag & drop file zones
    // =====================================================
    function autoGrow(ta) {
        ta.style.height = "auto";
        ta.style.height = ta.scrollHeight + "px";
    }
    document.querySelectorAll(".ed-field-autogrow").forEach(ta => {
        ta.addEventListener("input", () => autoGrow(ta));
    });

    document.querySelectorAll(".ed-file-drop").forEach(drop => {
        const input = drop.querySelector(".ed-file-drop-input");
        const text = drop.querySelector(".ed-file-drop-text");
        if (!input || !text) return;

        function refresh() {
            if (input.files && input.files[0]) {
                drop.classList.add("has-file");
                text.textContent = input.files[0].name;
            } else {
                drop.classList.remove("has-file");
                text.textContent = text.dataset.emptyText;
            }
        }
        input.addEventListener("change", refresh);

        ["dragenter", "dragover"].forEach(evt => drop.addEventListener(evt, (e) => {
            e.preventDefault();
            drop.classList.add("dragover");
        }));
        ["dragleave", "drop"].forEach(evt => drop.addEventListener(evt, (e) => {
            e.preventDefault();
            drop.classList.remove("dragover");
        }));
        drop.addEventListener("drop", (e) => {
            if (e.dataTransfer && e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                refresh();
            }
        });
    });

    // =====================================================
    // AI MODE RAIL + PANEL
    // =====================================================
    const panel = document.getElementById("edAiPanel");
    const panelTitle = document.getElementById("edAiPanelTitle");
    const panelDesc = document.getElementById("edAiPanelDesc");
    let currentModeKey = null;

    function modeBlockEl(key) { return document.querySelector(`[data-mode-block="${key}"]`); }

    window.closeModePanel = function () {
        panel.classList.remove("open");
        document.querySelectorAll(".ed-rail-icon").forEach(b => b.classList.remove("active"));
        currentModeKey = null;
    };

    function openModePanel(key) {
        const meta = MODE_BY_KEY[key];
        if (!meta) return;
        currentModeKey = key;
        panel.classList.add("open");
        document.querySelectorAll(".ed-rail-icon").forEach(b => b.classList.toggle("active", b.dataset.mode === key));
        panelTitle.textContent = `${meta.icon} ${meta.title}`;
        panelDesc.textContent = meta.desc;
        document.querySelectorAll(".ed-mode-block").forEach(b => { b.style.display = "none"; });
        const block = modeBlockEl(key);
        if (block) block.style.display = "block";
        renderMathIn(block);

        // mode1 has no input form — auto-start the conversation the first time it's opened
        if (key === "mode1" && block && block.dataset.started !== "1") {
            block.dataset.started = "1";
            submitModeStart(key, new FormData());
        }

        const messagesEl = block && block.querySelector(`[data-mode-messages="${key}"]`);
        if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    document.querySelectorAll(".ed-rail-icon").forEach(btn => {
        btn.addEventListener("click", () => {
            if (currentModeKey === btn.dataset.mode && panel.classList.contains("open")) {
                closeModePanel();
            } else {
                openModePanel(btn.dataset.mode);
            }
        });
    });

    function chatBubbleHtml(mode, msg) {
        const meta = MODE_BY_KEY[mode];
        if (msg.role === "user") {
            const div = document.createElement("div");
            div.textContent = msg.content;
            return `<div class="ed-chat-bubble ed-chat-bubble-user" data-msg-id="${msg.id}">${div.innerHTML}</div>`;
        }
        const escaped = (() => { const d = document.createElement("div"); d.textContent = msg.content; return d.innerHTML; })();
        const header = `<div class="ed-chat-bubble-header">${meta.icon} <span>${I18N.aiResponse || "Răspuns AI"}</span></div>`;
        if (meta.auto_insert) {
            return `<div class="ed-chat-bubble ed-chat-bubble-assistant" data-msg-id="${msg.id}">
                ${header}
                <div class="ed-chat-inserted">✅ ${I18N.insertedToDoc || "Adăugat în document"}</div>
                <button type="button" class="ed-chat-toggle" onclick="toggleChatDetail(this)">${I18N.showContent || "Arată conținutul"}</button>
                <div class="math-content ed-chat-detail hidden" data-math="${escaped}"></div>
            </div>`;
        }
        return `<div class="ed-chat-bubble ed-chat-bubble-assistant" data-msg-id="${msg.id}">
            ${header}
            <div class="math-content" data-math="${escaped}"></div>
            <button type="button" class="ed-chat-insert-btn" onclick="insertMessageToDoc('${mode}', ${msg.id}, this)">➕ ${I18N.insertToDoc || "Inserează în document"}</button>
        </div>`;
    }

    window.toggleChatDetail = function (btn) {
        const detail = btn.nextElementSibling;
        detail.classList.toggle("hidden");
        if (!detail.classList.contains("hidden")) renderMathIn(detail.parentElement);
        btn.textContent = detail.classList.contains("hidden")
            ? (I18N.showContent || "Arată conținutul")
            : (I18N.hideContent || "Ascunde conținutul");
    };

    function appendBubble(mode, msg) {
        const block = modeBlockEl(mode);
        const messagesEl = block.querySelector(`[data-mode-messages="${mode}"]`);
        messagesEl.insertAdjacentHTML("beforeend", chatBubbleHtml(mode, msg));
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function showTypingIndicator(mode) {
        const block = modeBlockEl(mode);
        const messagesEl = block && block.querySelector(`[data-mode-messages="${mode}"]`);
        if (!messagesEl) return;
        const el = document.createElement("div");
        el.className = "ed-typing-indicator";
        el.dataset.typingIndicator = "1";
        el.innerHTML = "<span></span><span></span><span></span>";
        messagesEl.appendChild(el);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    function hideTypingIndicator(mode) {
        const block = modeBlockEl(mode);
        const el = block && block.querySelector(`[data-typing-indicator="1"]`);
        if (el) el.remove();
    }

    function insertBlockIntoDoc(blockHtml) {
        docBody.insertAdjacentHTML("beforeend", blockHtml);
        docBody.querySelectorAll(".eq-box").forEach(wireEqBox);
        renderMathIn(docBody);
        scheduleAutosave();
        const nodes = docBody.querySelectorAll(".ai-block");
        if (nodes.length) nodes[nodes.length - 1].scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function switchBlockToChatMode(mode) {
        const block = modeBlockEl(mode);
        block.dataset.started = "1";
        block.querySelector(`[data-mode-start="${mode}"]`).style.display = "none";
        block.querySelector(`[data-mode-chat="${mode}"]`).style.display = "flex";
    }

    function submitModeStart(mode, formData) {
        const submitBtn = document.querySelector(`[data-mode-submit="${mode}"]`);
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Se generează..."; }
        toast("Se generează conținut...");

        fetch(`/editor/${documentId}/mode/${mode}/start`, { method: "POST", body: formData })
            .then(r => r.json())
            .then(data => {
                if (submitBtn) { submitBtn.disabled = false; }
                if (!data.ok) { toast(data.error || "Eroare", true); return; }
                switchBlockToChatMode(mode);
                appendBubble(mode, data.message);
                renderMathIn(modeBlockEl(mode));
                if (data.auto_insert && data.message.block_html) {
                    insertBlockIntoDoc(data.message.block_html);
                    toast("Conținut adăugat în document");
                }
            })
            .catch(() => { hideTypingIndicator(mode); toast("Eroare de rețea", true); if (submitBtn) submitBtn.disabled = false; });
    }

    document.querySelectorAll("[data-mode-start]").forEach(form => {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            const mode = form.dataset.modeStart;
            submitModeStart(mode, new FormData(form));
        });
    });

    document.querySelectorAll("[data-mode-message]").forEach(form => {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            const mode = form.dataset.modeMessage;
            const textarea = form.querySelector("textarea[name='prompt']");
            const prompt = textarea.value.trim();
            if (!prompt) return;
            textarea.value = "";
            sendModeMessage(mode, { prompt, action_type: "normal" });
        });
    });

    function sendModeMessage(mode, fields) {
        showTypingIndicator(mode);
        const fd = new FormData();
        Object.keys(fields).forEach(k => fd.append(k, fields[k]));
        fetch(`/editor/${documentId}/mode/${mode}/message`, { method: "POST", body: fd })
            .then(r => r.json())
            .then(data => {
                hideTypingIndicator(mode);
                if (!data.ok) { toast(data.error || "Eroare", true); return; }
                appendBubble(mode, data.message);
                renderMathIn(modeBlockEl(mode));
                if (data.auto_insert && data.message.block_html) {
                    insertBlockIntoDoc(data.message.block_html);
                    toast("Conținut adăugat în document");
                }
            })
            .catch(() => { hideTypingIndicator(mode); toast("Eroare de rețea", true); });
    }

    window.runQuickAction = function (mode, actionType, promptText) {
        sendModeMessage(mode, { prompt: promptText || "", action_type: actionType });
    };

    window.insertMessageToDoc = function (mode, messageId, btn) {
        fetch(`/editor/${documentId}/mode/${mode}/insert`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message_id: Number(messageId) })
        }).then(r => r.json()).then(data => {
            if (!data.ok) { toast("Eroare la inserare", true); return; }
            insertBlockIntoDoc(data.block_html);
            btn.disabled = true;
            btn.textContent = "✓ " + (I18N.insertedToDoc || "Inserat în document");
            toast(I18N.insertedToDoc || "Conținut adăugat în document");
        });
    };

})();
