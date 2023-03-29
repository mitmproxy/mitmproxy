// Adapted from https://stackoverflow.com/a/65996386/934719
/**
 * `navigator.clipboard.writeText()`, but with an additional fallback for non-secure contexts.
 */
import { ContentViewData } from "../components/contentviews/useContent";

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

export function copyFormattedViewContent(
    contentViewData: ContentViewData | undefined
) {
    let p = "";
    contentViewData?.lines.forEach((line) => {
        line.forEach((el) => (p = p + String(el[1])));
        p = p + "\n";
    });
    copyToClipboard(p);
}
