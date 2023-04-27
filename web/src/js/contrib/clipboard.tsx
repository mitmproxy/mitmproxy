// Adapted from https://stackoverflow.com/a/65996386/934719
/**
 * `navigator.clipboard.writeText()`, but with an additional fallback for non-secure contexts.
 */
export function copyToClipboard(text: string): Promise<void> {
    // navigator clipboard requires a security context such as https
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    } else {
        let t = document.createElement("textarea");
        t.value = text;
        t.style.position = "absolute";
        t.style.opacity = "0";
        document.body.appendChild(t);
        try {
            t.focus();
            t.select();
            document.execCommand("copy");
            return Promise.resolve();
        } catch (err) {
            alert(text);
            return Promise.reject(err);
        } finally {
            t.remove();
        }
    }
}
