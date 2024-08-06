import { getSpecs as getRegularModeSpecs } from "./regular";
import { getSpecs as getLocalModeSpecs } from "./local";
import { getSpecs as getWireguardModeSpecs } from "./wireguard";
import { getSpecs as getReverseModeSpecs } from "./reverse";
import { fetchApi, partition, rpartition } from "../../utils";
import { ServerInfo } from "../backendState";
import { ModesState } from "../modes";
import { ActionReducerMapBuilder, AsyncThunk, Draft } from "@reduxjs/toolkit";
import { AppAsyncThunkConfig } from "../hooks";

export interface ModeState {
    active: boolean;
    error?: string;
    listen_port?: number;
    listen_host?: string;
}

/**
 * Deprecated: use updateModes with createAppAsyncThunk.
 */
export const updateMode = () => {
    return async (_, getState) => {
        const modes = getState().modes;
        return await updateModeInner(modes);
    };
};

/**
 * Async thunk to update modes based on current UI state.
 */
export async function updateModes(_, thunkAPI) {
    const modes = thunkAPI.getState().modes;
    await updateModeInner(modes);
};

async function updateModeInner(modes: ModesState) {
    const activeModes: string[] = [
        ...getRegularModeSpecs(modes),
        ...getLocalModeSpecs(modes),
        ...getWireguardModeSpecs(modes),
        ...getReverseModeSpecs(modes),
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

export function addSetter<
    Type extends ModeState,
    Key extends keyof Draft<Type>,
>(
    builder: ActionReducerMapBuilder<Type>,
    attribute: Key,
    setThunk: AsyncThunk<void, Draft<Type>[Key], AppAsyncThunkConfig>,
) {
    builder.addCase(setThunk.pending, (state, action) => {
        state[attribute] = action.meta.arg;
        state.error = undefined;
    });
    builder.addCase(setThunk.rejected, (state, action) => {
        state.error = action.error.message;
    });
}

export const includeListenAddress = (
    modeNameAndData: string,
    state: Pick<ModeState, "listen_host" | "listen_port">,
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

export interface DecomposedMode {
    full_spec: string;
    name: string;
    data?: string;
    listen_host?: string;
    listen_port?: number;
}

export const parseMode = (full_spec: string): DecomposedMode => {
    let [head, listenAt] = rpartition(full_spec, "@");

    if (!head) {
        head = listenAt;
        listenAt = "";
    }

    const [name, data] = partition(head, ":");
    let listen_host: string | undefined, listen_port: number | undefined;

    if (listenAt) {
        let port: string;
        if (listenAt.includes(":")) {
            [listen_host, port] = rpartition(listenAt, ":");
        } else {
            listen_host = "";
            port = listenAt;
        }
        if (port) {
            listen_port = parseInt(port, 10);
            if (isNaN(listen_port) || listen_port < 0 || listen_port > 65535) {
                throw new Error(`invalid port: ${port}`);
            }
        }
    }
    return {
        full_spec,
        name,
        data,
        listen_host,
        listen_port,
    };
};

export const getModesOfType = (
    currentMode: string,
    servers: ServerInfo[],
): DecomposedMode[] => {
    return servers
        .filter((server) => server.type === currentMode)
        .map((server) => parseMode(server.full_spec));
};
