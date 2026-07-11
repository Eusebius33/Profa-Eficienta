/**
 * i18n.js — client-side language switching
 *
 * Uses /api/translations to fetch all translation keys, then updates every
 * [data-i18n] element and [data-i18n-placeholder] input/textarea on the page.
 * The chosen language is stored in a cookie so the server picks it up on the
 * next request (via `apply_language` in app.py).
 */

(function () {
    "use strict";

    // ── Helpers ──────────────────────────────────────────────────────────────

    function getCookie(name) {
        const match = document.cookie.match(new RegExp("(?:^|;)\\s*" + name + "=([^;]*)"));
        return match ? decodeURIComponent(match[1]) : null;
    }

    function setCookie(name, value, days) {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = name + "=" + encodeURIComponent(value) + "; expires=" + expires + "; path=/; SameSite=Lax";
    }

    function currentLang() {
        const param = new URLSearchParams(window.location.search).get("lang");
        return param || getCookie("lang") || "ro";
    }

    // ── Apply translations to the DOM ─────────────────────────────────────────

    function applyTranslations(translations, lang) {
        // Text content
        document.querySelectorAll("[data-i18n]").forEach(function (el) {
            const key = el.getAttribute("data-i18n");
            const entry = translations[key];
            if (!entry) return;
            const text = typeof entry === "object" ? (entry[lang] || entry["ro"] || "") : entry;
            if (text) el.textContent = text;
        });

        // Placeholders (input / textarea)
        document.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
            const key = el.getAttribute("data-i18n-placeholder");
            const entry = translations[key];
            if (!entry) return;
            const text = typeof entry === "object" ? (entry[lang] || entry["ro"] || "") : entry;
            if (text) el.setAttribute("placeholder", text);
        });

        // Title attribute
        document.querySelectorAll("[data-i18n-title]").forEach(function (el) {
            const key = el.getAttribute("data-i18n-title");
            const entry = translations[key];
            if (!entry) return;
            const text = typeof entry === "object" ? (entry[lang] || entry["ro"] || "") : entry;
            if (text) el.setAttribute("title", text);
        });
    }

    // ── Update navbar toggle button visual state ───────────────────────────────

    function updateLangToggle(lang) {
        ["ro", "en"].forEach(function (l) {
            const btn = document.getElementById("lang-toggle-" + l);
            if (!btn) return;
            if (l === lang) {
                btn.classList.add("font-bold", "text-cyan-400");
                btn.classList.remove("text-slate-400");
            } else {
                btn.classList.remove("font-bold", "text-cyan-400");
                btn.classList.add("text-slate-400");
            }
        });
    }

    // ── Public: switchLang ────────────────────────────────────────────────────

    /**
     * Called by the navbar RO / EN buttons.
     * Sets the cookie, re-fetches translations, and re-renders the page
     * text without a full reload.  The next server-side render will also
     * use the new language because `apply_language` reads the cookie.
     */
    window.switchLang = function (lang) {
        if (lang !== "ro" && lang !== "en") return;
        setCookie("lang", lang, 365);
        updateLangToggle(lang);

        fetch("/api/translations")
            .then(function (res) { return res.json(); })
            .then(function (translations) {
                applyTranslations(translations, lang);
            })
            .catch(function (err) {
                // If fetch fails, fall back to a full page reload so the
                // server renders the correct language server-side.
                console.warn("i18n: failed to fetch translations, reloading.", err);
                window.location.reload();
            });
    };

    // ── On page load: apply current language ──────────────────────────────────

    document.addEventListener("DOMContentLoaded", function () {
        const lang = currentLang();

        // Sync cookie so server stays in sync
        setCookie("lang", lang, 365);
        updateLangToggle(lang);

        // Only fetch and re-apply if we're NOT on Romanian (server default),
        // to avoid a redundant network round-trip on the happy path.
        if (lang !== "ro") {
            fetch("/api/translations")
                .then(function (res) { return res.json(); })
                .then(function (translations) {
                    applyTranslations(translations, lang);
                })
                .catch(function (err) {
                    console.warn("i18n: failed to fetch translations on load.", err);
                });
        }
    });
})();
