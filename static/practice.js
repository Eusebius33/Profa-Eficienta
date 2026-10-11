/* =============================================================
   PRACTICE — exercise generator

   The form describes a set (profile, chapters, difficulty, count, seed); the
   server builds it and hands back statements, answers and worked steps. The
   seed is shown because the same five values always rebuild the same set, so
   a teacher can hand a colleague a seed instead of a file.
   ============================================================= */
(function () {
    "use strict";

    var i18n = window.PRACTICE_I18N || {};
    var state = { exercises: [], selected: new Set(), active: null };

    var form = document.getElementById("practice-form");
    if (!form) return;

    var grid = document.getElementById("exercise-grid");
    var results = document.getElementById("practice-results");
    var panel = document.getElementById("detail-panel");
    var exportBar = document.getElementById("export-bar");
    var errorBox = document.getElementById("practice-error");
    var generateBtn = document.getElementById("generate-btn");
    var generateLabel = document.getElementById("generate-label");

    function renderMath(scope) {
        if (typeof window.renderMathInElement !== "function") return;
        try {
            window.renderMathInElement(scope, {
                delimiters: [
                    { left: "$$", right: "$$", display: true },
                    { left: "$", right: "$", display: false },
                    { left: "\\(", right: "\\)", display: false },
                    { left: "\\[", right: "\\]", display: true }
                ],
                throwOnError: false
            });
        } catch (err) { /* a bad expression must not blank the card */ }
    }

    function escapeHtml(value) {
        var d = document.createElement("div");
        d.textContent = value == null ? "" : value;
        return d.innerHTML;
    }

    /* ---------------- chip groups ---------------- */

    function groupValues(name) {
        return Array.prototype.slice
            .call(document.querySelectorAll('[data-chip-group="' + name + '"] .chip[aria-pressed="true"]'))
            .map(function (b) { return b.getAttribute("data-value"); });
    }

    document.querySelectorAll("[data-chip-group]").forEach(function (group) {
        var multi = group.hasAttribute("data-multi");
        group.addEventListener("click", function (e) {
            var chip = e.target.closest(".chip");
            if (!chip || chip.disabled || !group.contains(chip)) return;
            if (multi) {
                chip.setAttribute("aria-pressed", chip.getAttribute("aria-pressed") === "true" ? "false" : "true");
            } else {
                group.querySelectorAll(".chip").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
                chip.setAttribute("aria-pressed", "true");
                // Profile and level decide which chapters can be filled at all.
                refreshChapters();
            }
        });
    });

    /* A chapter with no template at this profile/level would return nothing,
       so it is disabled rather than silently producing a short set. */
    function refreshChapters() {
        var params = new URLSearchParams({
            profile: groupValues("profile")[0] || "",
            difficulty: groupValues("difficulty")[0] || ""
        });
        fetch("/practice/chapters?" + params.toString(), { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data || !data.ok) return;
                var bySlug = {};
                data.chapters.forEach(function (c) { bySlug[c.slug] = c; });
                document.querySelectorAll('[data-chip-group="chapters"] .chip').forEach(function (chip) {
                    var info = bySlug[chip.getAttribute("data-value")];
                    if (!info) return;
                    chip.disabled = !info.available;
                    if (!info.available) chip.setAttribute("aria-pressed", "false");
                });
            })
            .catch(function () { /* leave the chips as they are */ });
    }

    /* ---------------- count slider ---------------- */

    var count = document.getElementById("count");
    var countValue = document.getElementById("count-value");
    if (count && countValue) {
        count.addEventListener("input", function () { countValue.textContent = count.value; });
    }

    /* ---------------- generate ---------------- */

    function showError(message) {
        if (!errorBox) return;
        errorBox.textContent = message;
        errorBox.classList.toggle("hidden", !message);
    }

    function skeletonCards(n) {
        var out = "";
        for (var i = 0; i < n; i++) {
            out +=
                '<div class="rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">' +
                    '<div class="skeleton skeleton-line skeleton-line--4"></div>' +
                    '<div class="skeleton skeleton-block my-5"></div>' +
                    '<div class="skeleton skeleton-line skeleton-line--6"></div>' +
                "</div>";
        }
        return out;
    }

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var chapters = groupValues("chapters");
        if (!chapters.length) {
            showError(i18n.empty || "Alege cel puțin un capitol.");
            return;
        }
        showError("");

        var wanted = parseInt(count ? count.value : 10, 10) || 10;
        results.classList.remove("hidden");
        grid.innerHTML = skeletonCards(Math.min(wanted, 6));
        closePanel();
        generateBtn.disabled = true;

        fetch("/practice/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                profile: groupValues("profile")[0],
                difficulty: groupValues("difficulty")[0],
                chapters: chapters,
                count: wanted,
                seed: (document.getElementById("seed") || {}).value || ""
            })
        })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok || !res.body.ok) throw new Error(res.body && res.body.error);
                state.exercises = res.body.exercises;
                state.selected = new Set();
                document.getElementById("result-seed").textContent = res.body.seed;
                document.getElementById("result-count").textContent = res.body.exercises.length;
                // Writing the seed back makes the current set reproducible
                // without the teacher having to copy it by hand.
                var seedInput = document.getElementById("seed");
                if (seedInput) seedInput.value = res.body.seed;
                generateLabel.textContent = i18n.regenerate || generateLabel.textContent;
                renderCards();
                syncExportBar();
                results.scrollIntoView({ behavior: "smooth", block: "start" });
            })
            .catch(function (err) {
                grid.innerHTML = "";
                showError((err && err.message) || i18n.failed || "Generarea a eșuat.");
            })
            .then(function () { generateBtn.disabled = false; });
    });

    /* ---------------- cards ---------------- */

    function renderCards() {
        grid.innerHTML = "";
        state.exercises.forEach(function (ex) {
            var card = document.createElement("article");
            card.className = "ex-card turn-enter rounded-3xl border border-slate-200 bg-white p-6 shadow-lg";
            card.setAttribute("data-index", ex.index);
            card.innerHTML =
                '<div class="flex flex-wrap items-center gap-2">' +
                    '<span class="rounded-lg bg-cyan-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-cyan-700">' +
                        "Exercițiul " + ex.index + "</span>" +
                    '<span class="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">' +
                        escapeHtml(ex.chapter_label) + "</span>" +
                    '<span class="rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">' +
                        escapeHtml(ex.band) + "</span>" +
                "</div>" +
                '<div class="math-content mt-4 text-base leading-7 text-slate-900">' + ex.statement + "</div>" +
                '<div class="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">' +
                    // The hint button is a selection checkbox instead: picking
                    // exercises for a worksheet is what a teacher does here.
                    '<label class="press inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-cyan-400">' +
                        '<input type="checkbox" data-select="' + ex.index + '" class="accent-cyan-500">' +
                        escapeHtml(i18n.select || "Selectează") +
                    "</label>" +
                    '<span class="flex-1"></span>' +
                    '<button type="button" data-open="' + ex.index + '" data-focus="answer" class="press inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-cyan-400 hover:text-cyan-700">' +
                        escapeHtml(i18n.answer || "Răspuns") + "</button>" +
                    '<button type="button" data-open="' + ex.index + '" data-focus="steps" class="press inline-flex items-center gap-1.5 rounded-xl bg-slate-800 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700">' +
                        escapeHtml(i18n.steps || "Pași") + "</button>" +
                "</div>";
            grid.appendChild(card);
        });
        renderMath(grid);
    }

    grid.addEventListener("click", function (e) {
        var opener = e.target.closest("[data-open]");
        if (opener) {
            openPanel(parseInt(opener.getAttribute("data-open"), 10));
        }
    });

    grid.addEventListener("change", function (e) {
        var box = e.target.closest("[data-select]");
        if (!box) return;
        var index = parseInt(box.getAttribute("data-select"), 10);
        if (box.checked) state.selected.add(index); else state.selected.delete(index);
        var card = box.closest(".ex-card");
        if (card) card.classList.toggle("is-selected", box.checked);
        syncExportBar();
    });

    /* ---------------- detail panel ---------------- */

    function byIndex(index) {
        return state.exercises.filter(function (e) { return e.index === index; })[0];
    }

    function openPanel(index) {
        var ex = byIndex(index);
        if (!ex) return;
        state.active = index;

        grid.querySelectorAll(".ex-card").forEach(function (c) {
            c.classList.toggle("is-active", parseInt(c.getAttribute("data-index"), 10) === index);
        });

        document.getElementById("detail-index").textContent = "Exercițiul " + ex.index;
        document.getElementById("detail-chapter").textContent = ex.chapter_label;
        document.getElementById("detail-statement").innerHTML = ex.statement;
        document.getElementById("detail-answer").innerHTML = ex.answer || "—";

        var steps = document.getElementById("detail-steps");
        steps.innerHTML = "";
        (ex.steps || []).forEach(function (step, i) {
            var li = document.createElement("li");
            li.className = "math-content rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm leading-7 text-slate-800";
            li.innerHTML = '<span class="mr-1.5 font-bold text-cyan-600">' + (i + 1) + ".</span>" + step;
            steps.appendChild(li);
        });

        panel.classList.remove("hidden");
        renderMath(panel);
        if (window.innerWidth < 1024) panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function closePanel() {
        state.active = null;
        panel.classList.add("hidden");
        grid.querySelectorAll(".ex-card").forEach(function (c) { c.classList.remove("is-active"); });
    }

    document.getElementById("detail-close").addEventListener("click", closePanel);
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && state.active !== null) closePanel();
    });

    /* ---------------- selection + export ---------------- */

    function syncExportBar() {
        var n = state.selected.size;
        document.getElementById("selected-count").textContent = n;
        exportBar.hidden = n === 0;
    }

    function setAll(checked) {
        grid.querySelectorAll("[data-select]").forEach(function (box) {
            box.checked = checked;
            var index = parseInt(box.getAttribute("data-select"), 10);
            if (checked) state.selected.add(index); else state.selected.delete(index);
            var card = box.closest(".ex-card");
            if (card) card.classList.toggle("is-selected", checked);
        });
        syncExportBar();
    }

    document.getElementById("select-all").addEventListener("click", function () { setAll(true); });
    document.getElementById("clear-selection").addEventListener("click", function () { setAll(false); });

    exportBar.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-export]");
        if (!btn) return;
        var chosen = state.exercises.filter(function (ex) { return state.selected.has(ex.index); });
        if (!chosen.length) return;

        btn.disabled = true;
        fetch("/practice/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                format: btn.getAttribute("data-export"),
                exercises: chosen,
                include_solutions: document.getElementById("include-solutions").checked,
                title: document.getElementById("sheet-title").value
            })
        })
            .then(function (r) {
                if (!r.ok) throw new Error("export");
                return r.blob();
            })
            .then(function (blob) {
                var url = URL.createObjectURL(blob);
                var a = document.createElement("a");
                a.href = url;
                a.download = (document.getElementById("sheet-title").value || "fisa") +
                             "." + btn.getAttribute("data-export");
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
            })
            .catch(function () { showError(i18n.failed || "Exportul a eșuat."); })
            .then(function () { btn.disabled = false; });
    });

    refreshChapters();
})();
