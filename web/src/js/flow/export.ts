import { copyToClipboard, runCommand } from "../utils";
import { Flow } from "../flow";

export const copy = async (flow: Flow, format: string): Promise<void> => {
    // Safari: We need to call copyToClipboard _right away_ with a promise,
    // otherwise we're loosing user intent and can't copy anymore.
    const formatted = (async () => {
        const ret = await runCommand("export", format, `@${flow.id}`);
        if (ret.value) {
            return ret.value;
        } else if (ret.error) {
            throw ret.error;
        } else {
            throw ret;
        }
    })();
    try {
        await copyToClipboard(formatted);
    } catch (err) {
        alert(err);
    }
};
