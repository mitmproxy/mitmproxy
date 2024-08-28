import { getSpec as getRegularSpec } from "../../modes/regular";
import { getSpec as getLocalSpec } from "../../modes/local";
import { getSpec as getWireguardSpec } from "../../modes/wireguard";
import { getSpec as getReverseSpec } from "../../modes/reverse";
import { getSpec as getTransparentSpec } from "../../modes/transparent";
import { getSpec as getSocksSpec } from "../../modes/socks";
import { getSpec as getUpstreamSpec } from "../../modes/upstream";
import { getSpec as getDnsSpec } from "../../modes/dns";
import { fetchApi } from "../../utils";
import { BackendState } from "../backendState";
import {
    ActionReducerMapBuilder,
    AsyncThunk,
    Draft,
    PayloadAction,
} from "@reduxjs/toolkit";
import { AppAsyncThunkConfig, createAppAsyncThunk } from "../hooks";
import { ModeState, parseSpec, RawSpecParts } from "../../modes";

export const isActiveMode = (state: ModeState): boolean => {
    return state.active && !state.error;
};

/**
 * Async thunk to update modes based on current UI state.
 */
export async function updateModes(_, thunkAPI) {
    const modes = thunkAPI.getState().modes;
    const activeModes: string[] = [
        ...modes.regular.filter(isActiveMode).map(getRegularSpec),
        ...modes.local.filter(isActiveMode).map(getLocalSpec),
        ...modes.wireguard.filter(isActiveMode).map(getWireguardSpec),
        ...modes.reverse.filter(isActiveMode).map(getReverseSpec),
        ...modes.transparent.filter(isActiveMode).map(getTransparentSpec),
        ...modes.socks.filter(isActiveMode).map(getSocksSpec),
        ...modes.upstream.filter(isActiveMode).map(getUpstreamSpec),
        ...modes.dns.filter(isActiveMode).map(getDnsSpec),
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

export function updateState<M extends ModeState>(
    type: string,
    specPartsToState: (p: RawSpecParts) => M,
) {
    return function reducer(
        state: M[],
        action: PayloadAction<Partial<BackendState>>,
    ) {
        if (action.payload.servers) {
            const activeSpecs = Object.values(action.payload.servers)
                .filter((server) => server.type === type)
                .map((server) => parseSpec(server.full_spec));
            if (activeSpecs.length > 0) {
                return activeSpecs.map(specPartsToState);
            } else {
                for (const mode of state) {
                    mode.active = false;
                }
            }
        }
    };
}
