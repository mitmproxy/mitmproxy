// For Safari users.

export function copyToClipboard(text: string): Promise<void> {
    // navigator clipboard requires a security context such as https
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text).catch((err) => {
            console.error("Navigator clipboard failed:", err);
            return fallbackCopyTextToClipboard(text);
        });
    } else {
        return fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const textArea = document.createElement("textarea");
        textArea.value = text;

        // Ensure textarea is not visible and doesn't scroll the page
        textArea.style.position = "fixed"; // or absolute
        textArea.style.top = "0";
        textArea.style.left = "0";
        textArea.style.width = "2em";
        textArea.style.height = "2em";
        textArea.style.padding = "0";
        textArea.style.border = "none";
        textArea.style.outline = "none";
        textArea.style.boxShadow = "none";
        textArea.style.background = "transparent";

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand("copy");
            if (successful) {
                resolve();
            } else {
                console.error("Fallback copy was unsuccessful");
                alert(text);
                reject(new Error("Fallback copy failed"));
            }
        } catch (err) {
            console.error("Fallback copy error:", err);
            alert(text);
            reject(err);
        } finally {
            textArea.remove();
        }
    });
}
