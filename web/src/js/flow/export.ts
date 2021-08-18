import {fetchApi, runCommand} from "../utils";
import {Flow} from "../flow";

export const copy = async (flow: Flow, format: string): Promise<void> => {
    let ret = await runCommand("export", format, `@${flow.id}`);
    await navigator.clipboard.writeText(ret);
}
