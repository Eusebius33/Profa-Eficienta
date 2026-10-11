/* =============================================================
   ASYNC CHAT TURNS

   Every mode used to post the chat form normally: the browser sat on a blank
   navigation for as long as the model took, then the user's own message and
   the answer appeared together, after the fact. This sends the turn with
   fetch instead, so the user's message lands immediately and a skeleton holds
   the answer's place until it arrives.

   A mode opts in by giving its form `data-async-chat` and pointing it at the
   message list with `data-chat-target`. The server returns JSON for these
   requests and keeps its normal redirect for anything else, so the page still
   works with scripting unavailable.
   ============================================================= */
(function () {
    "use strict";

    var i18n = window.CHAT_I18N || {};

    function text(key, fallback) {
        return i18n[key] || fallback;
    }

    /* KaTeX is loaded by the layout; re-run it over whatever we just inserted. */
    function renderMath(scope) {
        if (typeof window.renderMathInElement !== "function") return;
        scope.querySelectorAll(".math-content, .msg-content-container").forEach(function (el) {
            try {
                window.renderMathInElement(el, {
                    delimiters: [
                        { left: "$$", right: "$$", display: true },
                        { left: "$", right: "$", display: false },
                        { left: "\\(", right: "\\)", display: false },
                        { left: "\\[", right: "\\]", display: true }
                    ],
                    throwOnError: false
                });
            } catch (err) { /* a bad expression must not take the turn down */ }
        });
    }

    function scrollToEnd(list) {
        list.scrollTop = list.scrollHeight;
    }

    function escapeHtml(value) {
        var div = document.createElement("div");
        div.textContent = value;
        return div.innerHTML;
    }

    /* The user's own message, shown the instant they send it. */
    function userBubble(body) {
        var wrap = document.createElement("div");
        wrap.className = "flex items-start justify-end gap-2 turn-enter";
        wrap.innerHTML =
            '<div class="bg-cyan-100 text-slate-900 p-4 rounded-2xl w-fit max-w-[max(36rem,72%)] border border-cyan-200">' +
            escapeHtml(body).replace(/\n/g, "<br>") +
            "</div>";
        return wrap;
    }

    function skeletonBubble(label) {
        var wrap = document.createElement("div");
        wrap.className = "flex items-start gap-2";
        wrap.setAttribute("data-chat-skeleton", "");
        wrap.innerHTML =
            '<div class="bg-slate-100 text-slate-900 p-5 rounded-2xl max-w-[max(48rem,88%)] border border-slate-200 w-full">' +
                '<div class="flex items-center gap-2 mb-4 text-slate-500">' +
                    '<span class="thinking-dots" aria-hidden="true"><span></span><span></span><span></span></span>' +
                    '<span class="text-xs font-semibold">' + escapeHtml(label) + "</span>" +
                "</div>" +
                '<div class="skeleton skeleton-line skeleton-line--full"></div>' +
                '<div class="skeleton skeleton-line skeleton-line--9"></div>' +
                '<div class="skeleton skeleton-line skeleton-line--8"></div>' +
                '<div class="skeleton skeleton-block my-4"></div>' +
                '<div class="skeleton skeleton-line skeleton-line--9"></div>' +
                '<div class="skeleton skeleton-line skeleton-line--6"></div>' +
                '<span class="sr-only" role="status" aria-live="polite">' + escapeHtml(label) + "</span>" +
            "</div>";
        return wrap;
    }

    function errorBubble(message) {
        var wrap = document.createElement("div");
        wrap.className = "flex items-start gap-2 turn-enter";
        wrap.innerHTML =
            '<div class="bg-rose-50 text-rose-900 p-4 rounded-2xl max-w-[max(48rem,88%)] border border-rose-200">' +
            '<p class="text-sm font-semibold">' + escapeHtml(text("failed", "Răspunsul nu a putut fi generat.")) + "</p>" +
            (message ? '<p class="mt-1 text-xs opacity-80">' + escapeHtml(message) + "</p>" : "") +
            "</div>";
        return wrap;
    }

    /* Replace the placeholder with the real turn, fading the two across each
       other rather than hard-cutting. */
    function swapSkeleton(skeleton, html, list) {
        var holder = document.createElement("div");
        holder.innerHTML = html;
        var nodes = Array.prototype.slice.call(holder.children);
        if (!nodes.length) {
            skeleton.remove();
            return;
        }
        skeleton.classList.add("skeleton-swap-out");
        window.setTimeout(function () {
            nodes.forEach(function (node) {
                node.classList.add("turn-enter");
                list.insertBefore(node, skeleton);
                renderMath(node);
            });
            skeleton.remove();
            scrollToEnd(list);
        }, 160);
    }

    function setBusy(form, busy) {
        form.querySelectorAll("button[type='submit'], [data-quick-action]").forEach(function (btn) {
            btn.disabled = busy;
        });
        document.querySelectorAll("[data-quick-action]").forEach(function (btn) {
            btn.disabled = busy;
        });
    }

    function send(form, payload, label) {
        var list = document.querySelector(form.getAttribute("data-chat-target") || "#chat");
        if (!list) return;

        var shown = payload.get("display_prompt") || payload.get("prompt") || "";
        payload.delete("display_prompt");

        if (shown) list.appendChild(userBubble(shown));
        var skeleton = skeletonBubble(label || text("thinking", "Se generează răspunsul…"));
        list.appendChild(skeleton);
        scrollToEnd(list);
        setBusy(form, true);

        fetch(form.getAttribute("action") || window.location.pathname, {
            method: "POST",
            body: payload,
            headers: { "X-Requested-With": "fetch" },
            credentials: "same-origin"
        })
            .then(function (res) {
                if (!res.ok) throw new Error("HTTP " + res.status);
                return res.json();
            })
            .then(function (data) {
                if (!data || !data.ok) throw new Error((data && data.error) || "");
                swapSkeleton(skeleton, data.html || "", list);
            })
            .catch(function (err) {
                skeleton.replaceWith(errorBubble(err && err.message));
                scrollToEnd(list);
            })
            .then(function () {
                setBusy(form, false);
            });
    }

    /* Quick actions used to paste their whole prompt into the textarea and
       submit the form. The prompt is the server's business now: the button
       sends only its action name, and `data-display` is the short line the
       teacher actually sees in the transcript. */
    function initQuickActions(form) {
        document.querySelectorAll("[data-quick-action]").forEach(function (btn) {
            // An input nested in the button (mode 2's exercise count) is a
            // parameter, not a second trigger.
            btn.querySelectorAll("input[data-param]").forEach(function (field) {
                field.addEventListener("click", function (e) { e.stopPropagation(); });
            });

            btn.addEventListener("click", function () {
                var payload = new FormData();
                payload.append("action_type", btn.getAttribute("data-quick-action"));
                payload.append("display_prompt", btn.getAttribute("data-display") || btn.textContent.trim());
                btn.querySelectorAll("input[data-param]").forEach(function (field) {
                    payload.append(field.getAttribute("data-param"), field.value);
                });
                send(form, payload, btn.getAttribute("data-label") || text("working", "Se lucrează…"));
            });
        });
    }

    function initForm(form) {
        var input = form.querySelector("[name='prompt']");
        var fileInput = form.querySelector("input[type='file']");

        form.addEventListener("submit", function (e) {
            var hasFile = fileInput && fileInput.files && fileInput.files.length;
            var body = input ? input.value.trim() : "";
            if (!body && !hasFile) {
                e.preventDefault();
                return;
            }
            e.preventDefault();

            var payload = new FormData(form);
            payload.set("action_type", "normal");
            payload.set("display_prompt", body || (fileInput.files[0] && fileInput.files[0].name) || "");

            if (input) {
                input.value = "";
                input.style.height = "auto";
            }
            if (fileInput) {
                fileInput.value = "";
                var chip = document.getElementById("attachChip");
                if (chip) chip.classList.add("hidden");
            }

            send(form, payload, text("thinking", "Se generează răspunsul…"));
        });

        initQuickActions(form);
    }

    /* First load of an upload-driven conversation. The page renders straight
       away with a skeleton; the transcription runs here instead of blocking
       the navigation, which is what used to strand the teacher on /menu. */
    function initBootstrap() {
        var host = document.querySelector("[data-chat-bootstrap]");
        if (!host) return;
        var list = document.querySelector(host.getAttribute("data-chat-target") || "#chat");
        var skeleton = list && list.querySelector("[data-chat-skeleton]");
        if (!list) return;

        fetch(host.getAttribute("data-chat-bootstrap"), {
            method: "POST",
            headers: { "X-Requested-With": "fetch" },
            credentials: "same-origin"
        })
            .then(function (res) {
                if (!res.ok) throw new Error("HTTP " + res.status);
                return res.json();
            })
            .then(function (data) {
                if (!data || !data.ok) throw new Error((data && data.error) || "");
                if (skeleton) {
                    swapSkeleton(skeleton, data.html || "", list);
                } else {
                    list.innerHTML = data.html || "";
                    renderMath(list);
                }
                document.querySelectorAll("[data-needs-transcription]").forEach(function (el) {
                    el.disabled = false;
                    el.removeAttribute("data-needs-transcription");
                });
            })
            .catch(function (err) {
                if (skeleton) skeleton.replaceWith(errorBubble(err && err.message));
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("form[data-async-chat]").forEach(initForm);
        initBootstrap();
        var list = document.getElementById("chat");
        if (list) scrollToEnd(list);
    });
})();
