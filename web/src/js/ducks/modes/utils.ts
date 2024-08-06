import { getSpecs as getRegularModeSpecs } from "./regular";
import { getSpecs as getLocalModeSpecs } from "./local";
import { getSpecs as getWireguardModeSpecs } from "./wireguard";
import { getSpecs as getReverseModeSpecs } from "./reverse";
import { fetchApi, partition, rpartition } from "../../utils";
import { ServerInfo } from "../backendState";
import { ModesState } from "../modes";
import { ActionReducerMapBuilder, AsyncThunk, Draft } from "@reduxjs/toolkit";
import { AppAsyncThunkConfig, createAppAsyncThunk } from "../hooks";

export interface ModeState {
    active: boolean;
    error?: string;
    listen_port?: number;
    listen_host?: string;
    // The UI ID is used to uniquely identify the server when doing async updates with createModeUpdateThunk
    ui_id?: number;
}

/**
 * FIXME: Remove before PR merge. This should be entirely replaced with updateModes.
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
async function updateModes(_, thunkAPI) {
    const modes = thunkAPI.getState().modes;
    await updateModeInner(modes);
}

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
}

export function createModeUpdateThunk<T>(type: string) {
    return createAppAsyncThunk<void, { server: ModeState; value: T }>(
        type,
        updateModes,
    );
}

export function addSetter<M extends ModeState, Attr extends keyof Draft<M>>(
    builder: ActionReducerMapBuilder<M[]>,
    attribute: Attr,
    setThunk: AsyncThunk<
        void,
        { server: ModeState; value: Draft<M>[Attr] },
        AppAsyncThunkConfig
    >,
) {
    builder.addCase(setThunk.pending, (state, action) => {
        const { server, value } = action.meta.arg;
        const idx = state.findIndex((m) => m.ui_id === server.ui_id);
        if (idx >= 0) {
            state[idx][attribute] = value;
            state[idx].error = undefined;
        }
    });
    builder.addCase(setThunk.rejected, (state, action) => {
        const { server } = action.meta.arg;
        const idx = state.findIndex((m) => m.ui_id === server.ui_id);
        if (idx >= 0) {
            state[idx].error = action.error.message;
        }
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

interface SpecParts {
    full_spec: string;
    name: string;
    data?: string;
    listen_host?: string;
    listen_port?: number;
}

export const parseSpec = (full_spec: string): SpecParts => {
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
    servers: { [key: string]: ServerInfo },
): SpecParts[] => {
    return Object.values(servers)
        .filter((server) => server.type === currentMode)
        .map((server) => parseSpec(server.full_spec));
};
