import {fetchApi, runCommand} from "../utils";
import {Flow} from "../flow";

function copyToClipboard(textToCopy) {
    // navigator clipboard requires a security context such as https
    if (navigator.clipboard && window.isSecureContext) {
        // navigator clipboard write text to the clipboard
        return navigator.clipboard.writeText(textToCopy);
    } else {
        // create text area
        let textArea = document.createElement("textarea");
        textArea.value = textToCopy;
        // make the text area not in the viewport, and set it to be invisible
        textArea.style.position = "absolute";
        textArea.style.opacity = String(0);
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        return new Promise((res, rej) => {
            // execute the copy command and remove the text box
            document.execCommand('copy') ? res() : rej();
            textArea.remove();

        });
    }
}

export const copy = async (flow: Flow, format: string): Promise<void> => {
    let ret = await runCommand("export", format, `@${flow.id}`);
    if (ret.value) {
        await copyToClipboard(ret.value);
    } else if (ret.error) {
        alert(ret.error)
    } else {
        console.error(ret);
    }
}
