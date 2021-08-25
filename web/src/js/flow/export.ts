import {fetchApi, runCommand} from "../utils";
import {Flow} from "../flow";

export const copy = async (flow: Flow, format: string): Promise<void> => {
    let ret = await runCommand("export", format, `@${flow.id}`);
    if(ret.value) {
        await navigator.clipboard.writeText(ret.value);
    } else if(ret.error) {
        alert(ret.error)
    } else {
        console.error(ret);
    }
}
