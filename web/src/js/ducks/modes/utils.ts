import { ModeState } from "../modes";
import { ReverseState } from "./reverse";

const isReverseState = (mode: ModeState): mode is ReverseState => {
    return "protocol" in mode;
};

export const addListenAddr = (mode: ModeState) => {
    let stringMode = mode.name;
    if (mode.active) {
        if (isReverseState(mode)) {
            stringMode += `:${mode.protocol}`;
        }
        if (mode.listen_host) {
            stringMode += `@${mode.listen_host}`;
        }
        if (mode.listen_port) {
            stringMode += `:${mode.listen_port}`;
        }
        return [stringMode];
    }
    return [];
};
