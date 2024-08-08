import { getSpec as getRegularSpec } from "../../modes/regular";
import { getSpec as getLocalSpec } from "../../modes/local";
import { getSpec as getWireguardSpec } from "../../modes/wireguard";
import { getSpec as getReverseSpec } from "../../modes/reverse";
import { fetchApi, partition, rpartition } from "../../utils";
import { ServerInfo } from "../backendState";
import type { ModesState } from "../modes";
import { ActionReducerMapBuilder, AsyncThunk, Draft } from "@reduxjs/toolkit";
import { AppAsyncThunkConfig, createAppAsyncThunk } from "../hooks";
import { ModeState } from "../../modes";

export const isActiveMode = (state: ModeState): boolean => {
    return state.active && !state.error;
};

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
        ...modes.regular.filter(isActiveMode).map(getRegularSpec),
        // FIXME: state should be an array itself
        ...Array(modes.local).filter(isActiveMode).map(getLocalSpec),
        ...modes.wireguard.filter(isActiveMode).map(getWireguardSpec),
        ...modes.reverse.filter(isActiveMode).map(getReverseSpec),
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
