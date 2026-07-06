const eyeIcon = `
<svg class="password-toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M2.25 12s3.5-6.25 9.75-6.25S21.75 12 21.75 12 18.25 18.25 12 18.25 2.25 12 2.25 12Z"></path>
  <circle cx="12" cy="12" r="2.75"></circle>
</svg>`;

const eyeOffIcon = `
<svg class="password-toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M3 3l18 18"></path>
  <path d="M10.6 10.6A2 2 0 0 0 12 14a2 2 0 0 0 1.4-.6"></path>
  <path d="M9.9 5.9A8.5 8.5 0 0 1 12 5.75c6.25 0 9.75 6.25 9.75 6.25a16.2 16.2 0 0 1-2.35 3.05"></path>
  <path d="M6.75 7.45C3.85 9.25 2.25 12 2.25 12s3.5 6.25 9.75 6.25c1.25 0 2.4-.25 3.45-.68"></path>
</svg>`;

function setupPasswordToggle() {
    const togglePassword = document.getElementById("togglePassword");
    const password = document.getElementById("password");

    if (!togglePassword || !password) return;

    togglePassword.innerHTML = eyeIcon;
    togglePassword.addEventListener("click", () => {
        const isPassword = password.getAttribute("type") === "password";
        password.setAttribute("type", isPassword ? "text" : "password");
        togglePassword.innerHTML = isPassword ? eyeOffIcon : eyeIcon;
        togglePassword.setAttribute("aria-label", isPassword ? "Ascunde parola" : "Arata parola");
    });
}

function setupMobileNav() {
    const toggle = document.querySelector(".mobile-nav-toggle");
    const menu = document.querySelector(".mobile-nav-links");
    if (!toggle || !menu) return;

    toggle.addEventListener("click", () => {
        const isOpen = document.body.classList.toggle("mobile-nav-open");
        toggle.setAttribute("aria-expanded", String(isOpen));
    });

    menu.querySelectorAll("a, button").forEach((item) => {
        item.addEventListener("click", () => {
            document.body.classList.remove("mobile-nav-open");
            toggle.setAttribute("aria-expanded", "false");
        });
    });
}

function setupMobilePanels() {
    const appShell = document.querySelector('div[class*="max-w-[1850px]"]');
    if (!appShell) return;

    const panels = appShell.querySelectorAll(':scope > div[class*="w-72"], :scope > div[class*="w-80"]');
    panels.forEach((panel, index) => {
        if (panel.dataset.mobilePanelReady) return;
        panel.dataset.mobilePanelReady = "true";
        panel.classList.add("mobile-collapsible-panel");
        if (index > 0) panel.classList.add("is-collapsed");

        const heading = panel.querySelector("h2")?.textContent?.trim() || (index === 0 ? "Conversatii" : "Resurse");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "mobile-panel-toggle";
        button.innerHTML = `<span>${heading}</span><span class="mobile-panel-chevron">+</span>`;
        button.addEventListener("click", () => {
            panel.classList.toggle("is-collapsed");
            button.querySelector(".mobile-panel-chevron").textContent = panel.classList.contains("is-collapsed") ? "+" : "-";
        });
        panel.prepend(button);
    });
}

function setupPromptForms() {
    document.querySelectorAll("form").forEach((form) => {
        const textarea = form.querySelector("textarea");
        const submit = form.querySelector('button[type="submit"], button:not([type])');
        if (!textarea || !submit || form.dataset.promptReady) return;

        form.dataset.promptReady = "true";
        form.classList.add("mobile-prompt-composer");
        submit.addEventListener("click", () => {
            if (!form.checkValidity()) return;
            submit.dataset.originalText = submit.textContent.trim();
            submit.classList.add("is-loading");
            submit.textContent = "Se trimite...";
        });
    });
}


function setupCopyButtons() {
    const icon = `<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
    document.querySelectorAll(".copy-btn, .copy-math-btn").forEach((button) => {
        if (button.dataset.copyUiReady) return;
        button.dataset.copyUiReady = "true";
        button.classList.add("standard-copy-action");
        button.setAttribute("aria-label", button.getAttribute("aria-label") || "Copiaza raspunsul");
        button.setAttribute("title", button.getAttribute("title") || "Copiaza raspunsul");
        if (!button.querySelector("svg")) {
            button.insertAdjacentHTML("afterbegin", icon);
        }
    });
}

function removeDemoPlaceholders() {
    const demoNeedles = [
        "2024-2025 Proba E",
        "BAC Simulare 1",
        "Teste trigonometrie",
        "Clasa IX - radicali",
        "Trigonometrie - baze",
        "Ecuatii",
        "Ecuații",
        "exercitiu 1",
        "exercitiu 2",
        "exercitiu 3",
        "exercițiu 1",
        "exercițiu 2",
        "exercițiu 3"
    ];

    document.querySelectorAll("li, div").forEach((node) => {
        const text = node.textContent.trim();
        if (demoNeedles.some((needle) => text === needle)) {
            node.remove();
        }
    });
}
function setupEmptyStates() {
    const chat = document.getElementById("chat");
    if (chat && !chat.querySelector(".bg-cyan-100, .bg-slate-100")) {
        chat.innerHTML = '<div class="empty-state">Incepe cu o cerere sau alege o actiune rapida.</div>';
    }

    document.querySelectorAll("ul, .space-y-2").forEach((list) => {
        const hasContent = Array.from(list.children).some((child) => child.textContent.trim());
        if (!hasContent && !list.querySelector(".empty-state")) {
            list.innerHTML = '<div class="empty-state empty-state--compact">Nu exista elemente inca.</div>';
        }
    });
}

function setupFileUploadPreview() {
    const fileUpload = document.getElementById("fileUpload");
    const fileList = document.getElementById("fileList");

    if (!fileUpload || !fileList) return;

    fileUpload.addEventListener("change", () => {
        fileList.innerHTML = "";
        Array.from(fileUpload.files).forEach((file) => {
            const item = document.createElement("div");
            item.className = "bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-300 text-sm";
            item.textContent = `Fisier: ${file.name}`;
            fileList.appendChild(item);
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupPasswordToggle();
    setupMobileNav();
    setupMobilePanels();
    setupPromptForms();
    setupEmptyStates();
    setupFileUploadPreview();
});