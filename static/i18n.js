// i18n.js
// Client-side translation engine

let currentLang = 'ro';
let translations = {};

// Function to get a cookie value by name
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Function to set a cookie
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/";
}

// Fetch translations from the server
async function loadTranslations() {
    try {
        const response = await fetch('/api/translations');
        if (response.ok) {
            translations = await response.json();
            applyTranslations();
        } else {
            console.error("Failed to load translations");
        }
    } catch (error) {
        console.error("Error loading translations:", error);
    }
}

// Apply translations to all elements with data-i18n or data-i18n-placeholder
function applyTranslations() {
    // Update text content
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[key] && translations[key][currentLang]) {
            el.innerHTML = translations[key][currentLang];
        }
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (translations[key] && translations[key][currentLang]) {
            el.placeholder = translations[key][currentLang];
        }
    });

    // Update active state in UI toggles if they exist
    const roToggle = document.getElementById('lang-toggle-ro');
    const enToggle = document.getElementById('lang-toggle-en');

    if(roToggle && enToggle) {
        if(currentLang === 'ro') {
            roToggle.classList.add('font-bold', 'text-cyan-400');
            enToggle.classList.remove('font-bold', 'text-cyan-400');
        } else {
            enToggle.classList.add('font-bold', 'text-cyan-400');
            roToggle.classList.remove('font-bold', 'text-cyan-400');
        }
    }
}

// Function to switch language, save to cookie, and apply
function switchLang(lang) {
    if (lang === 'ro' || lang === 'en') {
        currentLang = lang;
        setCookie('lang', lang, 365); // Save for 1 year
        applyTranslations();
        window.location.reload();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Read saved language from cookie, default to 'ro'
    const savedLang = getCookie('lang');
    if (savedLang === 'en' || savedLang === 'ro') {
        currentLang = savedLang;
    }

    loadTranslations();
});
