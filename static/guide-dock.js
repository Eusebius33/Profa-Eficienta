/* =============================================================
   GUIDE DOCK

   A small chat that only answers "where in this app do I do X?". It is backed
   by ai.website_guide(), which used to be reachable only if a Mode 1
   conversation happened to be titled "Ghid Website" -- so in practice nobody
   ever saw it. Mode 1 is now the teaching assistant; routing lives here.

   The thread is kept in the session server side, so it survives navigation
   between pages without needing a conversation record.
   ============================================================= */
(function () {
    "use strict";

    var toggle = document.getElementById("guide-toggle");
    var dock = document.getElementById("guide-dock");
    if (!toggle || !dock) return;

    var list = document.getElementById("guide-messages");
    var form = document.getElementById("guide-form");
    var input = document.getElementById("guide-input");
    var suggestions = document.getElementById("guide-suggestions");
    var closeBtn = document.getElementById("guide-close");
    var i18n = window.GUIDE_I18N || {};
    var busy = false;

    function open() {
        dock.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        if (input) input.focus();
        list.scrollTop = list.scrollHeight;
    }

    function close() {
        dock.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
    }

    toggle.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !dock.hidden) close();
    });

    function bubble(kind, html) {
        var el = document.createElement("div");
        el.className = "guide-msg guide-msg--" + kind;
        el.innerHTML = html;
        list.appendChild(el);
        list.scrollTop = list.scrollHeight;
        return el;
    }

    function escapeHtml(value) {
        var d = document.createElement("div");
        d.textContent = value == null ? "" : value;
        return d.innerHTML;
    }

    function skeleton() {
        var el = document.createElement("div");
        el.className = "guide-skeleton";
        el.innerHTML =
            '<div class="skeleton skeleton-line skeleton-line--full"></div>' +
            '<div class="skeleton skeleton-line skeleton-line--8"></div>' +
            '<div class="skeleton skeleton-line skeleton-line--6"></div>';
        list.appendChild(el);
        list.scrollTop = list.scrollHeight;
        return el;
    }

    function ask(question) {
        if (busy || !question.trim()) return;
        busy = true;
        // The openers are a cold start only; once the conversation has begun
        // they would just be noise.
        if (suggestions) suggestions.innerHTML = "";
        bubble("me", escapeHtml(question));
        var pending = skeleton();

        fetch("/api/guide", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ message: question })
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                pending.remove();
                if (!data || !data.ok) throw new Error(data && data.error);
                bubble("bot", data.html);
            })
            .catch(function () {
                pending.remove();
                bubble("error", escapeHtml(i18n.error || "Ghidul nu a putut răspunde."));
            })
            .then(function () { busy = false; });
    }

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var value = input.value.trim();
        if (!value) return;
        input.value = "";
        input.style.height = "auto";
        ask(value);
    });

    // Enter sends, Shift+Enter makes a new line -- the usual chat contract.
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event("submit", { cancelable: true }));
        }
    });

    input.addEventListener("input", function () {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 112) + "px";
    });

    if (suggestions) {
        suggestions.addEventListener("click", function (e) {
            var chip = e.target.closest("[data-guide-ask]");
            if (chip) ask(chip.getAttribute("data-guide-ask"));
        });
    }
})();
