/**
 * serverState houses properties about the current mitmproxy instance that are not options,
 * e.g. the list of available content views or the current version.
 */

import { createAction, createSlice } from "@reduxjs/toolkit";

export const STATE_RECEIVE = createAction<BackendState>("STATE_RECEIVE");
export const STATE_UPDATE = createAction<Partial<BackendState>>("STATE_UPDATE");

export interface ServerInfo {
    description: string;
    full_spec: string;
    is_running: boolean;
    last_exception: string | null;
    listen_addrs: ([string, number] | [string, number, number, number])[];
    type: string;
    wireguard_conf?: string;
    tun_name?: string;
}

export interface BackendState {
    version: string;
    contentViews: string[];
    servers: { [key: string]: ServerInfo };
    platform: string;
    localModeUnavailable: string | null;
}
export interface BackendStateExtra extends BackendState {
    available: boolean;
}

export const defaultState: BackendStateExtra = {
    available: false,
    version: "",
    contentViews: [],
    servers: {},
    platform: "",
    localModeUnavailable: null,
};

const backendStateSlice = createSlice({
    name: "backendState",
    initialState: defaultState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(STATE_RECEIVE, (state, action) => {
                return {
                    ...state,
                    available: true,
                    ...action.payload,
                };
            })
            .addCase(STATE_UPDATE, (state, action) => {
                return {
                    ...state,
                    ...action.payload,
                };
            });
    },
});

export default backendStateSlice.reducer;
