(function () {
    "use strict";

    // Set by an inline <script> in index.html to this page's own mount path
    // ("/cadoul-matematic" once folded into the main app, "" when this runs
    // standalone) — prefixed onto every fetch() below so the API calls keep
    // working under either mount point.
    var API_BASE = window.WAITLIST_BASE || "";

    var REDUCE_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var HOVER_FINE = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

    /* ---------------------------------------------------------------------
     * Reveal-on-scroll: adds .is-visible to .reveal elements as they enter
     * the viewport. Plain DOM, no React needed for this — it's presentation,
     * not interactive state.
     * ------------------------------------------------------------------- */
    function setupReveal() {
        var els = document.querySelectorAll(".reveal");
        if (!els.length) return;

        if (!("IntersectionObserver" in window)) {
            els.forEach(function (el) { el.classList.add("is-visible"); });
            return;
        }

        var io = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        io.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
        );

        els.forEach(function (el) { io.observe(el); });
    }

    /* ---------------------------------------------------------------------
     * Card tilt: subtle 3D rotation following the pointer, mouse/trackpad
     * only (gated on hover+fine pointer so touch never gets a stuck tilt),
     * and only once a card has finished its own entrance reveal so the two
     * transforms never fight each other. Applies to every [data-tilt]
     * element — waitlist cards, the WhatsApp card, and testimonial cards
     * all share this one behavior.
     * ------------------------------------------------------------------- */
    function setupTilt() {
        if (REDUCE_MOTION || !HOVER_FINE) return;
        var cards = document.querySelectorAll("[data-tilt]");
        cards.forEach(function (card) {
            var frame = null;

            function onMove(e) {
                if (!card.classList.contains("is-visible")) return;
                var rect = card.getBoundingClientRect();
                var px = (e.clientX - rect.left) / rect.width;
                var py = (e.clientY - rect.top) / rect.height;
                var rotateY = (px - 0.5) * 7;
                var rotateX = (0.5 - py) * 7;
                if (frame) cancelAnimationFrame(frame);
                frame = requestAnimationFrame(function () {
                    card.style.transform =
                        "perspective(900px) rotateX(" + rotateX.toFixed(2) + "deg) rotateY(" +
                        rotateY.toFixed(2) + "deg) translateY(-4px)";
                });
            }

            function onLeave() {
                if (frame) cancelAnimationFrame(frame);
                card.style.transform = "";
            }

            card.addEventListener("mousemove", onMove);
            card.addEventListener("mouseleave", onLeave);
        });
    }

    setupReveal();
    setupTilt();

    /* ---------------------------------------------------------------------
     * Shared form helpers — React islands mounted with React.createElement
     * (no JSX/Babel needed, just the React/ReactDOM UMD builds).
     * ------------------------------------------------------------------- */
    var h = React.createElement;
    var EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    var PHONE_RE = /^0\d{9}$/;

    function normalizePhoneClient(raw) {
        var digits = (raw || "").replace(/[^\d+]/g, "");
        if (digits.indexOf("+40") === 0) digits = "0" + digits.slice(3);
        else if (digits.indexOf("0040") === 0) digits = "0" + digits.slice(4);
        else if (digits.indexOf("40") === 0 && digits.length === 11) digits = "0" + digits.slice(2);
        return digits;
    }

    function shakeEl(el) {
        if (!el || REDUCE_MOTION) return;
        el.classList.remove("wf-shake");
        void el.offsetWidth; // force reflow so the animation can replay
        el.classList.add("wf-shake");
        setTimeout(function () {
            if (el) el.classList.remove("wf-shake");
        }, 240);
    }

    function getSource() {
        try {
            var params = new URLSearchParams(window.location.search);
            var utm = params.get("utm_source");
            if (utm) return utm.slice(0, 100);
            if (document.referrer) {
                return new URL(document.referrer).hostname.slice(0, 100);
            }
        } catch (e) { /* ignore malformed referrer/URL */ }
        return "";
    }
    var SOURCE = getSource();

    // Success celebration: mounts in the "out" state (already painted), then
    // flips to "in" on the next frame so the CSS transition/keyframes in
    // styles.css actually animate instead of snapping straight to the end
    // state. The checkmark path length is measured at runtime rather than
    // hardcoded, per the stroke-draw technique. Shared by every form.
    function SuccessBlock(props) {
        var rootRef = React.useRef(null);
        var pathRef = React.useRef(null);
        var _state = React.useState("out");
        var state = _state[0], setState = _state[1];

        React.useEffect(function () {
            if (pathRef.current && rootRef.current) {
                var len = pathRef.current.getTotalLength();
                rootRef.current.style.setProperty("--path-length", String(len));
            }
            var raf = requestAnimationFrame(function () { setState("in"); });
            return function () { cancelAnimationFrame(raf); };
        }, []);

        return h(
            "div",
            { ref: rootRef, className: "wf-success", "data-state": state, role: "status", "aria-live": "polite" },
            h(
                "span",
                { className: "wf-success-icon", "aria-hidden": "true" },
                h(
                    "svg",
                    { width: 13, height: 13, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 3, strokeLinecap: "round", strokeLinejoin: "round" },
                    h("path", { ref: pathRef, className: "wf-success-path", d: "M5 13l4 4L19 7" })
                )
            ),
            h(
                "div",
                { className: "wf-success-text" },
                h("div", { className: "wf-success-title" }, props.title),
                h("div", { className: "wf-success-desc" }, props.desc)
            )
        );
    }

    function successCopy(tier, alreadyRegistered) {
        if (alreadyRegistered) {
            return {
                title: "Ești deja pe listă.",
                desc: "Nu-ți face griji, ești acoperit — te anunțăm de îndată ce lansăm.",
            };
        }
        if (tier === "vip") {
            return {
                title: "Ești pe lista VIP.",
                desc: "Accesul timpuriu, luna gratuită și suportul 24/7 sunt rezervate pe numele tău. Te anunțăm primul.",
            };
        }
        return {
            title: "Prezentarea este pe drum.",
            desc: "Îți trimitem un semn de îndată ce lansăm.",
        };
    }

    /* ---------------------------------------------------------------------
     * Free / VIP waitlist form. Free posts straight to /api/waitlist. VIP
     * additionally collects a phone number and, instead of a direct
     * success state, POSTs to /api/vip-checkout and redirects the browser
     * to the returned Stripe Checkout URL — the actual "success" happens on
     * Stripe's hosted page and back on /vip-success after payment.
     * ------------------------------------------------------------------- */
    function WaitlistForm(props) {
        var tier = props.tier;
        var isVip = tier === "vip";
        var cta = props.cta || "Trimite";
        var uid = React.useId();
        var inputId = "wf-email-" + uid;
        var phoneId = "wf-phone-" + uid;
        var errorId = "wf-error-" + uid;
        var inputRef = React.useRef(null);
        var phoneRef = React.useRef(null);

        var _email = React.useState("");
        var email = _email[0], setEmail = _email[1];
        var _phone = React.useState("");
        var phone = _phone[0], setPhone = _phone[1];
        var _hp = React.useState("");
        var hp = _hp[0], setHp = _hp[1];
        var _touched = React.useState(false);
        var touched = _touched[0], setTouched = _touched[1];
        var _status = React.useState("idle"); // idle | loading | success | error
        var status = _status[0], setStatus = _status[1];
        var _errorMsg = React.useState("");
        var errorMsg = _errorMsg[0], setErrorMsg = _errorMsg[1];
        var _already = React.useState(false);
        var already = _already[0], setAlready = _already[1];

        var isEmailValid = EMAIL_RE.test(email.trim());
        var isPhoneValid = !isVip || PHONE_RE.test(normalizePhoneClient(phone));
        var showEmailError = touched && !isEmailValid;
        var showPhoneError = touched && isVip && !isPhoneValid;

        function handleSubmit(e) {
            e.preventDefault();
            if (status === "loading") return;

            setTouched(true);
            if (!isEmailValid) { shakeEl(inputRef.current); return; }
            if (isVip && !isPhoneValid) { shakeEl(phoneRef.current); return; }

            setStatus("loading");
            setErrorMsg("");

            var endpoint = API_BASE + (isVip ? "/api/vip-checkout" : "/api/waitlist");
            var body = { email: email.trim(), source: SOURCE, hp_field: hp };
            if (isVip) {
                body.phone = phone.trim();
            } else {
                body.tier = tier;
            }

            fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            })
                .then(function (res) {
                    return res.json().then(function (data) {
                        return { ok: res.ok, data: data };
                    });
                })
                .then(function (result) {
                    if (result.data && result.data.ok) {
                        if (isVip && result.data.url) {
                            window.location.href = result.data.url;
                            return;
                        }
                        setAlready(!!result.data.already_registered);
                        setStatus("success");
                    } else {
                        setErrorMsg((result.data && result.data.message) || "A apărut o eroare. Mai încearcă o dată.");
                        setStatus("error");
                        shakeEl(inputRef.current);
                    }
                })
                .catch(function () {
                    setErrorMsg("Nu am putut trimite. Verifică conexiunea și încearcă din nou.");
                    setStatus("error");
                    shakeEl(inputRef.current);
                });
        }

        if (status === "success") {
            var copy = successCopy(tier, already);
            return h(SuccessBlock, { title: copy.title, desc: copy.desc });
        }

        var honeypot = h("input", {
            type: "text",
            name: "hp_field",
            className: "wf-hp",
            tabIndex: -1,
            autoComplete: "off",
            "aria-hidden": "true",
            value: hp,
            onChange: function (e) { setHp(e.target.value); },
        });

        var loadingContent = h(
            React.Fragment,
            null,
            h("span", { className: "wf-spinner", "aria-hidden": "true" }),
            isVip ? "Se redirecționează..." : "Se trimite..."
        );

        if (isVip) {
            return h(
                "form",
                { className: "wf-form", onSubmit: handleSubmit, noValidate: true },
                h(
                    "div",
                    { className: "wf-field" },
                    h("label", { className: "wf-label", htmlFor: inputId }, "Adresa ta de email"),
                    h("input", {
                        id: inputId,
                        ref: inputRef,
                        className: "wf-input",
                        type: "email",
                        name: "email",
                        inputMode: "email",
                        autoComplete: "email",
                        placeholder: "nume@mail.com",
                        required: true,
                        maxLength: 254,
                        value: email,
                        "aria-invalid": showEmailError ? "true" : "false",
                        onChange: function (e) { setEmail(e.target.value); },
                        onBlur: function () { setTouched(true); },
                    }),
                    showEmailError && h("p", { className: "wf-error" }, "Introdu o adresă de email validă.")
                ),
                h(
                    "div",
                    { className: "wf-field" },
                    h("label", { className: "wf-label", htmlFor: phoneId }, "Numărul tău de telefon"),
                    h("input", {
                        id: phoneId,
                        ref: phoneRef,
                        className: "wf-input",
                        type: "tel",
                        name: "phone",
                        inputMode: "tel",
                        autoComplete: "tel",
                        placeholder: "07XX XXX XXX",
                        required: true,
                        value: phone,
                        "aria-invalid": showPhoneError ? "true" : "false",
                        onChange: function (e) { setPhone(e.target.value); },
                        onBlur: function () { setTouched(true); },
                    }),
                    showPhoneError && h("p", { className: "wf-error" }, "Introdu un număr de telefon valid (ex: 07XX XXX XXX).")
                ),
                honeypot,
                h(
                    "button",
                    { type: "submit", className: "wf-submit wf-submit--block", disabled: status === "loading" },
                    status === "loading" ? loadingContent : cta
                ),
                status === "error" && h("p", { className: "wf-error", id: errorId, role: "alert" }, errorMsg)
            );
        }

        return h(
            "form",
            { className: "wf-form", onSubmit: handleSubmit, noValidate: true },
            h(
                "div",
                { className: "wf-field" },
                h("label", { className: "wf-label", htmlFor: inputId }, "Adresa ta de email"),
                h(
                    "div",
                    { className: "wf-input-row" },
                    h("input", {
                        id: inputId,
                        ref: inputRef,
                        className: "wf-input",
                        type: "email",
                        name: "email",
                        inputMode: "email",
                        autoComplete: "email",
                        placeholder: "nume@mail.com",
                        required: true,
                        maxLength: 254,
                        value: email,
                        "aria-invalid": showEmailError ? "true" : "false",
                        "aria-describedby": showEmailError || status === "error" ? errorId : undefined,
                        onChange: function (e) { setEmail(e.target.value); },
                        onBlur: function () { setTouched(true); },
                    }),
                    h(
                        "button",
                        { type: "submit", className: "wf-submit", disabled: status === "loading" },
                        status === "loading" ? loadingContent : cta
                    )
                ),
                honeypot,
                (showEmailError || status === "error") &&
                    h(
                        "p",
                        { className: "wf-error", id: errorId, role: "alert" },
                        showEmailError ? "Introdu o adresă de email validă." : errorMsg
                    )
            )
        );
    }

    /* ---------------------------------------------------------------------
     * WhatsApp group interest form — phone number only.
     * ------------------------------------------------------------------- */
    function WhatsAppForm(props) {
        var cta = props.cta || "Trimite";
        var uid = React.useId();
        var phoneId = "wa-phone-" + uid;
        var errorId = "wa-error-" + uid;
        var phoneRef = React.useRef(null);

        var _phone = React.useState("");
        var phone = _phone[0], setPhone = _phone[1];
        var _hp = React.useState("");
        var hp = _hp[0], setHp = _hp[1];
        var _touched = React.useState(false);
        var touched = _touched[0], setTouched = _touched[1];
        var _status = React.useState("idle");
        var status = _status[0], setStatus = _status[1];
        var _errorMsg = React.useState("");
        var errorMsg = _errorMsg[0], setErrorMsg = _errorMsg[1];
        var _already = React.useState(false);
        var already = _already[0], setAlready = _already[1];

        var isPhoneValid = PHONE_RE.test(normalizePhoneClient(phone));
        var showError = touched && !isPhoneValid;

        function handleSubmit(e) {
            e.preventDefault();
            if (status === "loading") return;
            setTouched(true);
            if (!isPhoneValid) { shakeEl(phoneRef.current); return; }

            setStatus("loading");
            setErrorMsg("");

            fetch(API_BASE + "/api/whatsapp", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone: phone.trim(), source: SOURCE, hp_field: hp }),
            })
                .then(function (res) {
                    return res.json().then(function (data) {
                        return { ok: res.ok, data: data };
                    });
                })
                .then(function (result) {
                    if (result.data && result.data.ok) {
                        setAlready(!!result.data.already_registered);
                        setStatus("success");
                    } else {
                        setErrorMsg((result.data && result.data.message) || "A apărut o eroare. Mai încearcă o dată.");
                        setStatus("error");
                        shakeEl(phoneRef.current);
                    }
                })
                .catch(function () {
                    setErrorMsg("Nu am putut trimite. Verifică conexiunea și încearcă din nou.");
                    setStatus("error");
                    shakeEl(phoneRef.current);
                });
        }

        if (status === "success") {
            var copy = already
                ? { title: "Ești deja în grup.", desc: "Numărul tău e deja pe listă — te contactăm noi în curând." }
                : { title: "Cerere trimisă!", desc: "Verificăm manual cererile pentru Cancelaria de pe WhatsApp și te adăugăm în curând." };
            return h(SuccessBlock, { title: copy.title, desc: copy.desc });
        }

        return h(
            "form",
            { className: "wf-form", onSubmit: handleSubmit, noValidate: true },
            h(
                "div",
                { className: "wf-field" },
                h("label", { className: "wf-label", htmlFor: phoneId }, "Numărul tău de telefon"),
                h(
                    "div",
                    { className: "wf-input-row" },
                    h("input", {
                        id: phoneId,
                        ref: phoneRef,
                        className: "wf-input",
                        type: "tel",
                        name: "phone",
                        inputMode: "tel",
                        autoComplete: "tel",
                        placeholder: "07XX XXX XXX",
                        required: true,
                        value: phone,
                        "aria-invalid": showError ? "true" : "false",
                        "aria-describedby": showError || status === "error" ? errorId : undefined,
                        onChange: function (e) { setPhone(e.target.value); },
                        onBlur: function () { setTouched(true); },
                    }),
                    h(
                        "button",
                        { type: "submit", className: "wf-submit", disabled: status === "loading" },
                        status === "loading" ? h(React.Fragment, null, h("span", { className: "wf-spinner", "aria-hidden": "true" }), "Se trimite...") : cta
                    )
                ),
                h("input", {
                    type: "text",
                    name: "hp_field",
                    className: "wf-hp",
                    tabIndex: -1,
                    autoComplete: "off",
                    "aria-hidden": "true",
                    value: hp,
                    onChange: function (e) { setHp(e.target.value); },
                }),
                (showError || status === "error") &&
                    h(
                        "p",
                        { className: "wf-error", id: errorId, role: "alert" },
                        showError ? "Introdu un număr de telefon valid (ex: 07XX XXX XXX)." : errorMsg
                    )
            )
        );
    }

    function mountForms() {
        var mounts = document.querySelectorAll('[id^="waitlist-root-"]');
        mounts.forEach(function (el) {
            var tier = el.getAttribute("data-tier");
            var cta = el.getAttribute("data-cta") || "Trimite";
            var root = ReactDOM.createRoot(el);
            root.render(h(WaitlistForm, { tier: tier, cta: cta }));
        });

        var waEl = document.getElementById("whatsapp-root");
        if (waEl) {
            var waCta = waEl.getAttribute("data-cta") || "Trimite";
            ReactDOM.createRoot(waEl).render(h(WhatsAppForm, { cta: waCta }));
        }
    }

    mountForms();
})();
