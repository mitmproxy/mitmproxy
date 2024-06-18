import { ModeState } from "../modes";

export const addListenAddr = (mode: ModeState) => {
    let stringMode = mode.name;
    if (mode.active) {
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
