/**
 * serverState houses properties about the current mitmproxy instance that are not options,
 * e.g. the list of available content views or the current version.
 */

import { createAction, PayloadAction } from "@reduxjs/toolkit";

export const RECEIVE = createAction<Partial<BackendState>>("STATE_RECEIVE");
export const UPDATE = createAction<Partial<BackendState>>("STATE_UPDATE");

export interface ServerInfo {
    description: string;
    full_spec: string;
    is_running: boolean;
    last_exception: string | null;
    listen_addrs: [string, number][];
    type: string;
    wireguard_conf?: string;
    tun_name?: string;
}

export interface BackendState {
    available: boolean;
    version: string;
    contentViews: string[];
    servers: { [key: string]: ServerInfo };
    platform: string;
    localModeUnavailable: string | null;
}

export const defaultState: BackendState = {
    available: false,
    version: "",
    contentViews: [],
    servers: {},
    platform: "",
    localModeUnavailable: null,
};

export function mockUpdate(newState: Partial<BackendState>) {
    return {
        type: UPDATE.type,
        payload: newState,
    };
}

export default function reducer(state = defaultState, action): BackendState {
    switch (action.type) {
        case RECEIVE.type:
        case UPDATE.type:
            return {
                ...state,
                available: true,
                ...(action as PayloadAction<Partial<BackendState>>).payload,
            };
        default:
            return state;
    }
}
