// copyMath.js
// Universal utility to copy KaTeX/MathML rendered content to the clipboard 
// in a format (text/html) that Microsoft Word can parse into native equations.

async function copyMathToClipboard(buttonElement, containerElement) {
    try {
        if (!containerElement) {
            console.error("No container provided for copy");
            return;
        }

        // Clone the container to clean it up before copying
        const clone = containerElement.cloneNode(true);
        
        // Remove any copy buttons inside the clone so they aren't pasted into Word
        const copyBtns = clone.querySelectorAll('.copy-math-btn');
        copyBtns.forEach(btn => btn.remove());

        // Ensure all <math> tags have the xmlns attribute required by Microsoft Word
        const mathEls = clone.querySelectorAll('math');
        mathEls.forEach(mathEl => {
            mathEl.setAttribute("xmlns", "http://www.w3.org/1998/Math/MathML");
            // Word prefers display="block" for block equations if not inline
            if (!mathEl.hasAttribute("display")) {
                mathEl.setAttribute("display", "inline");
            }
        });

        // Some cleanup for KaTeX specific HTML so Word only sees the MathML 
        // (Word sometimes gets confused if both HTML presentation and MathML are present).
        // KaTeX places MathML inside .katex-mathml and HTML inside .katex-html.
        // We can just strip out .katex-html so only MathML remains in the clipboard!
        const katexHtml = clone.querySelectorAll('.katex-html');
        katexHtml.forEach(el => el.remove());

        // Get the pure HTML
        const htmlContent = clone.innerHTML;
        const textContent = clone.innerText;

        const blobHtml = new Blob([htmlContent], { type: 'text/html' });
        const blobText = new Blob([textContent], { type: 'text/plain' });
        
        const clipboardItem = new ClipboardItem({
            'text/html': blobHtml,
            'text/plain': blobText
        });
        
        await navigator.clipboard.write([clipboardItem]);
        
        // Visual feedback on the button
        const originalHTML = buttonElement.innerHTML;
        buttonElement.innerHTML = `<svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
        buttonElement.classList.add('bg-green-100', 'border-green-200');
        
        setTimeout(() => {
            buttonElement.innerHTML = originalHTML;
            buttonElement.classList.remove('bg-green-100', 'border-green-200');
        }, 2000);
        
    } catch (err) {
        console.error('Failed to copy text: ', err);
        alert('Failed to copy to clipboard. Ensure you are on a secure context (HTTPS/localhost).');
    }
}
