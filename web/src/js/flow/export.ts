import {runCommand} from "../utils";
import {Flow} from "../flow";
import {copyToClipboard} from "../contrib/clipboard";


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
