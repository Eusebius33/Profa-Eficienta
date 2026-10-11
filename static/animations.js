(function () {
    "use strict";

    var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function applyStagger() {
        document.querySelectorAll("[data-reveal-group]").forEach(function (group) {
            Array.from(group.children).forEach(function (child, i) {
                child.classList.add("reveal");
                child.style.setProperty("--stagger-index", Math.min(i, 6));
            });
        });
        document.querySelectorAll("[data-stagger-index]").forEach(function (el) {
            el.style.setProperty("--stagger-index", el.getAttribute("data-stagger-index"));
        });
    }

    function initVisibilityToggles() {
        var targets = document.querySelectorAll(".reveal, .draw-line, .step-fill, .badge-pop, .rule-grow");
        if (reducedMotion || !("IntersectionObserver" in window)) {
            targets.forEach(function (el) { el.classList.add("is-visible"); });
            return;
        }
        // A .step-fill rests at scaleX(0)/scaleY(0), so its own box has zero area and
        // browsers decide intersection for it inconsistently -- it comes down to the
        // sub-pixel x of each bar, which left random bars stuck unfilled. Watch the
        // full-size track wrapping each fill instead.
        var watched = new Map();
        targets.forEach(function (el) {
            var watch = el.classList.contains("step-fill") && el.parentElement ? el.parentElement : el;
            var group = watched.get(watch);
            if (group) { group.push(el); } else { watched.set(watch, [el]); }
        });
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                io.unobserve(entry.target);
                (watched.get(entry.target) || []).forEach(function (el) {
                    el.style.willChange = "transform, opacity";
                    el.classList.add("is-visible");
                    window.setTimeout(function () {
                        el.style.willChange = "";
                        // The entrance is over; stop owning this element's
                        // `transition` so its hover rules run at hover speed.
                        if (el.classList.contains("reveal")) el.classList.add("reveal-done");
                    }, 900 + (parseInt(el.style.getPropertyValue("--stagger-index"), 10) || 0) * 65);
                });
            });
        }, { threshold: 0.15, rootMargin: "0px 0px -6% 0px" });
        watched.forEach(function (group, watch) { io.observe(watch); });
    }

    function easeOutCubic(p) {
        return 1 - Math.pow(1 - p, 3);
    }

    function animateCounter(el) {
        var target = parseFloat(el.dataset.countTo);
        if (Number.isNaN(target)) return;
        var suffix = el.dataset.countSuffix || "";
        var duration = parseInt(el.dataset.countDuration || "1400", 10);
        if (reducedMotion) {
            el.textContent = target + suffix;
            return;
        }
        var start = performance.now();
        function tick(now) {
            var p = Math.min((now - start) / duration, 1);
            var val = Math.round(target * easeOutCubic(p));
            el.textContent = val + suffix;
            if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    function initCounters() {
        var counters = document.querySelectorAll("[data-count-to]");
        if (!counters.length) return;
        if (!("IntersectionObserver" in window)) {
            counters.forEach(animateCounter);
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.6 });
        counters.forEach(function (el) { io.observe(el); });
    }

    function initTilt() {
        var canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
        if (!canHover || reducedMotion) return;
        document.querySelectorAll(".tilt-card").forEach(function (card) {
            card.addEventListener("mousemove", function (e) {
                var rect = card.getBoundingClientRect();
                var px = (e.clientX - rect.left) / rect.width;
                var py = (e.clientY - rect.top) / rect.height;
                card.style.setProperty("--rx", ((0.5 - py) * 6).toFixed(2) + "deg");
                card.style.setProperty("--ry", ((px - 0.5) * 8).toFixed(2) + "deg");
                card.style.setProperty("--x", (px * 100).toFixed(1) + "%");
                card.style.setProperty("--y", (py * 100).toFixed(1) + "%");
            });
            card.addEventListener("mouseleave", function () {
                card.style.setProperty("--rx", "0deg");
                card.style.setProperty("--ry", "0deg");
            });
        });
    }

    function initAccordion() {
        document.querySelectorAll("[data-accordion]").forEach(function (group) {
            var items = group.querySelectorAll("[data-accordion-item]");
            items.forEach(function (item) {
                var trigger = item.querySelector("[data-accordion-trigger]");
                if (!trigger) return;
                trigger.setAttribute("aria-expanded", "false");
                trigger.addEventListener("click", function () {
                    var isOpen = item.classList.contains("is-open");
                    items.forEach(function (i) {
                        i.classList.remove("is-open");
                        var t = i.querySelector("[data-accordion-trigger]");
                        if (t) t.setAttribute("aria-expanded", "false");
                    });
                    if (!isOpen) {
                        item.classList.add("is-open");
                        trigger.setAttribute("aria-expanded", "true");
                    }
                });
            });
        });
    }

    function initNavScrollState() {
        var nav = document.querySelector("nav");
        if (!nav) return;
        var update = function () {
            nav.classList.toggle("is-scrolled", window.scrollY > 8);
        };
        update();
        window.addEventListener("scroll", update, { passive: true });
    }

    function initScrollspy() {
        var links = document.querySelectorAll("[data-toc-link]");
        if (!links.length || !("IntersectionObserver" in window)) return;
        var sections = Array.from(links)
            .map(function (link) { return document.getElementById(link.getAttribute("data-toc-link")); })
            .filter(Boolean);
        if (!sections.length) return;
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                var link = document.querySelector('[data-toc-link="' + entry.target.id + '"]');
                if (!link || !entry.isIntersecting) return;
                links.forEach(function (l) { l.classList.remove("is-active"); });
                link.classList.add("is-active");
            });
        }, { rootMargin: "-20% 0px -70% 0px", threshold: 0 });
        sections.forEach(function (section) { io.observe(section); });
    }

    /* The one orchestrated page-load moment: the headline rises word by word.
       Above-the-fold copy should not wait on a scroll reveal, so this fires on
       load rather than through the IntersectionObserver. */
    function initSplitHeadings() {
        var targets = document.querySelectorAll("[data-split-words]");
        if (!targets.length || reducedMotion) return;
        targets.forEach(function (el) {
            var words = el.textContent.trim().split(/\s+/);
            if (words.length < 2) return;
            el.textContent = "";
            words.forEach(function (word, i) {
                var outer = document.createElement("span");
                outer.className = "word";
                outer.style.setProperty("--word-index", i);
                var inner = document.createElement("span");
                inner.className = "word-inner";
                inner.textContent = word;
                outer.appendChild(inner);
                el.appendChild(outer);
                // A real space between words, so the line still wraps naturally.
                if (i < words.length - 1) el.appendChild(document.createTextNode(" "));
            });
            el.classList.add("is-split");
        });
        // Two frames: one for the split layout to land, one to flip the state so
        // the transition actually runs instead of being collapsed into the paint.
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                targets.forEach(function (el) { el.classList.add("is-revealed"); });
            });
        });
    }

    /* Scroll position is the clock here, so the bar carries no easing: the CSS
       sets the transform straight from this value. */
    function initScrollProgress() {
        var bar = document.querySelector(".scroll-progress");
        if (!bar) return;
        var queued = false;
        function update() {
            queued = false;
            var max = document.documentElement.scrollHeight - window.innerHeight;
            var progress = max > 0 ? Math.min(window.scrollY / max, 1) : 0;
            bar.style.setProperty("--progress", progress.toFixed(4));
        }
        function schedule() {
            if (queued) return;
            queued = true;
            requestAnimationFrame(update);
        }
        update();
        window.addEventListener("scroll", schedule, { passive: true });
        window.addEventListener("resize", schedule, { passive: true });
    }

    /* Looping decoration burns GPU even when it is scrolled out of sight. */
    function initAmbientPause() {
        if (!("IntersectionObserver" in window)) return;
        var loops = document.querySelectorAll(".orb, .math-glyph, .marquee-track");
        if (!loops.length) return;
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                entry.target.style.animationPlayState = entry.isIntersecting ? "running" : "paused";
            });
        }, { threshold: 0 });
        loops.forEach(function (el) { io.observe(el); });
    }

    document.addEventListener("DOMContentLoaded", function () {
        applyStagger();
        initVisibilityToggles();
        initSplitHeadings();
        initCounters();
        initTilt();
        initAccordion();
        initNavScrollState();
        initScrollspy();
        initScrollProgress();
        initAmbientPause();
    });
})();
