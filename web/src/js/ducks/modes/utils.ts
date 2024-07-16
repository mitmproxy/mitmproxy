import { getMode as getRegularModeConfig } from "./regular";
import { getMode as getLocalModeConfig } from "./local";
import { getMode as getWireguardModeConfig } from "./wireguard";
import { getMode as getReverseModeConfig } from "./reverse";
import { fetchApi, partition, rpartition } from "../../utils";
import { ServerInfo } from "../backendState";

export interface ModeState {
    active: boolean;
    listen_port?: number;
    listen_host?: string;
    error?: string;
}

/**
 * Update modes based on current UI state.
 *
 * Raises an error if the update is unsuccessful.
 */
export const updateMode = () => {
    return async (_, getState) => {
        const modes = getState().modes;

        const activeModes: string[] = [
            ...getRegularModeConfig(modes),
            ...getLocalModeConfig(modes),
            ...getWireguardModeConfig(modes),
            ...getReverseModeConfig(modes),
            //add new modes here
        ];
        const response = await fetchApi.put("/options", {
            mode: activeModes,
        });
        if (response.status === 200) {
            return;
        } else {
            throw new Error(await response.text());
        }
    };
};

export const includeModeState = (
    modeNameAndData: string,
    state: ModeState,
): string[] => {
    let mode = modeNameAndData;
    if (!state.active || state.error) {
        return [];
    }
    if (state.listen_host && state.listen_port) {
        mode += `@${state.listen_host}:${state.listen_port}`;
    } else if (state.listen_port) {
        mode += `@${state.listen_port}`;
    }
    return [mode];
};

export const parseMode = (spec: string) => {
    let [head, listenAt] = rpartition(spec, "@");

    if (!head) {
        head = listenAt;
        listenAt = "";
    }

    const [mode, data] = partition(head, ":");
    let host = "",
        port: string | number = "";

    if (listenAt) {
        if (listenAt.includes(":")) {
            [host, port] = rpartition(listenAt, ":");
        } else {
            host = "";
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
        data: data ? data : "",
        listen_host: host,
        listen_port: port,
    };
};

export const getModesOfType = (currentMode: string, servers: ServerInfo[]) => {
    return servers
        .filter((server) => server.type === currentMode)
        .map((server) => parseMode(server.full_spec));
};
