import { getMode as getRegularModeConfig } from "./regular";
import { getMode as getLocalModeConfig } from "./local";
import { fetchApi } from "../../utils";

export interface ModeState {
    active: boolean;
    name: string;
    listen_port?: number;
    listen_host?: string;
    error?: string;
}

export const updateMode = () => {
    return async (_, getState) => {
        try {
            const modes = getState().modes;

            const activeModes: string[] = [
                ...getRegularModeConfig(modes),
                ...getLocalModeConfig(modes),
                //add new modes here
            ];
            const response = await fetchApi.put("/options", {
                mode: activeModes,
            });
            if (response.status === 200) {
                return { success: true };
            } else {
                const errorText = await response.text();
                return { success: false, error: errorText };
            }
        } catch (error) {
            //TODO: handle error
        }
    };
};

export const addListenAddr = (mode: ModeState) => {
    let stringMode = mode.name;
    if (mode.active) {
        if (mode.listen_host && mode.listen_port) {
            stringMode += `@${mode.listen_host}:${mode.listen_port}`;
        } else if (mode.listen_port) {
            stringMode += `@${mode.listen_port}`;
        }
        return [stringMode];
    }
    return [];
};

export const parseMode = (spec: string) => {
    const [head, listenAt] = spec.includes("@") ? spec.split("@") : [spec, ""];
    const [mode, data] = head.includes(":") ? head.split(":") : [head, ""];

    let host = "";
    let port: string | number = "";

    if (listenAt) {
        if (listenAt.includes(":")) {
            [host, port] = listenAt.split(":");
        } else {
            port = listenAt;
        }

        if (port) {
            port = parseInt(port, 10);
            if (isNaN(port) || port < 0 || port > 65535) {
                throw new Error(`invalid port: ${port}`);
            }
        }
    }

    return {
        name: mode,
        data: data,
        listen_host: host,
        listen_port: port,
    };
};

export const getModesOfType = (currentMode: string, modes: string[]) => {
    return modes
        .filter((mode) => mode.startsWith(currentMode))
        .map((mode) => parseMode(mode));
};
