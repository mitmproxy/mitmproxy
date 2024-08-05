import { getSpecs as getRegularModeSpecs } from "./regular";
import { getSpecs as getLocalModeSpecs } from "./local";
import { getSpecs as getWireguardModeSpecs } from "./wireguard";
import { getSpecs as getReverseModeSpecs } from "./reverse";
import { fetchApi, partition, rpartition } from "../../utils";
import { ServerInfo } from "../backendState";

export interface ModeState {
    active: boolean;
    error?: string;
}

export interface ModeStateWithListenAddress extends ModeState {
    listen_port?: number;
    listen_host?: string;
}

/**
 * Update modes based on current UI state.
 *
 * Raises an error if the update is unsuccessful.
 */
export const updateMode = () => {
    return async (_, getState) => {
        const modes = getState().modes;

        const modeSpecs: string[] = [
            ...getRegularModeSpecs(modes),
            ...getLocalModeSpecs(modes),
            ...getWireguardModeSpecs(modes),
            ...getReverseModeSpecs(modes),
            //add new modes here
        ];
        const response = await fetchApi.put("/options", {
            mode: modeSpecs,
        });
        if (response.status === 200) {
            return;
        } else {
            throw new Error(await response.text());
        }
    };
};

export const includeListenAddress = (
    modeNameAndData: string,
    state: ModeStateWithListenAddress,
): string => {
    if (state.listen_host && state.listen_port) {
        return `${modeNameAndData}@${state.listen_host}:${state.listen_port}`;
    } else if (state.listen_port) {
        return `${modeNameAndData}@${state.listen_port}`;
    } else {
        return modeNameAndData;
    }
};

export const isActiveMode = (state: ModeState): boolean => {
    return state.active && !state.error;
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
