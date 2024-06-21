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

const parseMode = (modeConfig) => {
    /*examples:
        "regular@http:8081" or "regular@8081" or "regular"
        "local:google,curl" or "local"
        "reverse:http://host" or "reverse:https://host" or "reverse:http://host:8081"
    */
    if (modeConfig.includes(":")) {
        if (modeConfig.startsWith("local")) {
            return {
                name: "local",
                applications: modeConfig.substring("local:".length),
            };
        }
        const [name, listen] = modeConfig.split("@");
        const [listen_host, listen_port] = listen.split(":");
        const listen_port_num = parseInt(listen_port);
        return { name, listen_host, listen_port: listen_port_num };
    } else if (modeConfig.includes("@")) {
        const [name, listen_port] = modeConfig.split("@");
        const listen_port_num = parseInt(listen_port);
        return { name, listen_port: listen_port_num };
    } else {
        return { name: modeConfig };
    }
};

export const getModesOfType = (currentMode: string, modes: string[]) => {
    return modes
        .filter((mode) => mode.startsWith(currentMode))
        .map((mode) => parseMode(mode));
};
