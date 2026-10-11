/* ============================================================
   EXPORT SHEET (modes 1-4)

   Picking several AI replies and turning them into ONE printable
   worksheet is the point of the checkboxes, so the UI has to read that
   way: each picked reply shows the section it will become ("Subiectul
   II"), and the toolbar says how many are going into the document.

   Nothing downloads straight away - both buttons open a dialog first, so
   the teacher says what the sheet is (title, type, class) before the file
   exists. Leaving it all blank is allowed and produces a bare, numbered
   exercise sheet.
   ============================================================ */

const ExportSheet = (function () {

    const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
                   "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"];

    function roman(n) {
        return ROMAN[n - 1] || String(n);
    }

    function boxes() {
        return Array.from(document.querySelectorAll('input[name="message_ids"]'));
    }

    function checked() {
        return boxes().filter((b) => b.checked);
    }

    /* ---- live labels: "Include în fișă" -> "Subiectul II" ---- */
    function refresh() {
        const all = boxes();
        const picked = checked();
        const many = picked.length > 1;

        all.forEach((box) => {
            const text = box.parentElement && box.parentElement.querySelector(".sheet-pick-text");
            if (!text) return;

            if (!box.checked) {
                text.textContent = "Include în fișă";
                box.parentElement.classList.remove("sheet-pick--on");
                return;
            }

            const index = picked.indexOf(box) + 1;
            text.textContent = many ? "Subiectul " + roman(index) : "În fișă";
            box.parentElement.classList.add("sheet-pick--on");
        });

        const counter = document.getElementById("sheetCount");
        if (counter) {
            const n = picked.length;
            counter.textContent =
                n === 0 ? "Niciun răspuns selectat"
              : n === 1 ? "1 răspuns în fișă"
              : n + " răspunsuri în fișă";
            counter.classList.toggle("text-slate-400", n === 0);
            counter.classList.toggle("text-cyan-700", n > 0);
        }

        // Section headings only make sense once there are 2+ replies.
        const sectionRow = document.getElementById("sheetSectionsRow");
        if (sectionRow) {
            sectionRow.classList.toggle("hidden", picked.length < 2);
        }
    }

    function setAll(state) {
        boxes().forEach((b) => { b.checked = state; });
        refresh();
    }

    /* ---- dialog ---- */
    let pendingIds = null;   // null => whatever is ticked in the chat

    function open(format, onlyMessageId) {
        const dialog = document.getElementById("sheetDialog");
        const form = document.getElementById("sheetForm");
        if (!dialog || !form) return;

        pendingIds = (onlyMessageId === undefined || onlyMessageId === null)
            ? checked().map((b) => b.value)
            : [String(onlyMessageId)];

        if (!pendingIds.length) {
            alert("Selectează cel puțin un răspuns pentru a crea fișa.");
            return;
        }

        form.action = form.dataset.actionBase + "/" + format;

        const note = document.getElementById("sheetDialogNote");
        if (note) {
            note.textContent = pendingIds.length === 1
                ? "1 răspuns va intra în fișă."
                : pendingIds.length + " răspunsuri vor intra în fișă, în ordinea din conversație.";
        }

        const sectionsRow = document.getElementById("sheetDialogSections");
        if (sectionsRow) {
            sectionsRow.classList.toggle("hidden", pendingIds.length < 2);
        }

        dialog.classList.remove("hidden");
        dialog.classList.add("flex");

        const first = document.getElementById("docTitle");
        if (first) setTimeout(() => first.focus(), 30);
    }

    function close() {
        const dialog = document.getElementById("sheetDialog");
        if (!dialog) return;
        dialog.classList.add("hidden");
        dialog.classList.remove("flex");
        pendingIds = null;
    }

    /* Copy the chosen ids into the dialog's own form right before it posts -
       the checkboxes live out in the chat, not inside this form. */
    function prepareSubmit(form) {
        form.querySelectorAll('input[name="message_ids"]').forEach((el) => el.remove());

        (pendingIds || []).forEach((id) => {
            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "message_ids";
            hidden.value = id;
            form.appendChild(hidden);
        });

        // A browser download leaves the page in place, so re-enable the button
        // instead of leaving the dialog looking stuck.
        setTimeout(close, 400);
        return true;
    }

    function init() {
        if (!boxes().length) return;

        boxes().forEach((box) => box.addEventListener("change", refresh));
        refresh();

        const dialog = document.getElementById("sheetDialog");
        if (dialog) {
            dialog.addEventListener("click", function (e) {
                if (e.target === dialog) close();
            });
        }

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") close();
        });
    }

    document.addEventListener("DOMContentLoaded", init);

    return { open, close, setAll, prepareSubmit, refresh };
})();

// Kept so any older markup that still calls it keeps working.
function setAllExportChecks(checked) {
    ExportSheet.setAll(checked);
}
