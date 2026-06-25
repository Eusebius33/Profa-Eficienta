document.addEventListener("DOMContentLoaded", () => {

    const togglePassword = document.getElementById("togglePassword");
    const password = document.getElementById("password");

    // ruleaza doar daca exista elementele pe pagina
    if (togglePassword && password) {

        togglePassword.addEventListener("click", () => {

            const type =
                password.getAttribute("type") === "password"
                    ? "text"
                    : "password";

            password.setAttribute("type", type);

            togglePassword.textContent =
                type === "password"
                    ? "👁"
                    : "🙈";
        });
    }
});

// upload preview
document.addEventListener("DOMContentLoaded", () => {

    const fileUpload = document.getElementById("fileUpload");
    const fileList = document.getElementById("fileList");

    if (fileUpload && fileList) {

        fileUpload.addEventListener("change", () => {

            fileList.innerHTML = "";

            Array.from(fileUpload.files).forEach((file) => {

                const item = document.createElement("div");

                item.className =
                    "bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-300 text-sm";

                item.textContent = `📎 ${file.name}`;

                fileList.appendChild(item);
            });
        });
    }
});
