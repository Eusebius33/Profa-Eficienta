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
        var targets = document.querySelectorAll(".reveal, .draw-line, .step-fill, .badge-pop");
        if (reducedMotion || !("IntersectionObserver" in window)) {
            targets.forEach(function (el) { el.classList.add("is-visible"); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                var el = entry.target;
                el.style.willChange = "transform, opacity";
                el.classList.add("is-visible");
                window.setTimeout(function () { el.style.willChange = ""; }, 900);
                io.unobserve(el);
            });
        }, { threshold: 0.15, rootMargin: "0px 0px -6% 0px" });
        targets.forEach(function (el) { io.observe(el); });
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

    document.addEventListener("DOMContentLoaded", function () {
        applyStagger();
        initVisibilityToggles();
        initCounters();
        initTilt();
        initAccordion();
        initNavScrollState();
        initScrollspy();
    });
})();
