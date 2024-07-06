/**
 * serverState houses properties about the current mitmproxy instance that are not options,
 * e.g. the list of available content views or the current version.
 */

export const RECEIVE = "STATE_RECEIVE";
export const UPDATE = "STATE_UPDATE";

export interface ServerInfo {
    description: string;
    full_spec: string;
    is_running: boolean;
    last_exception: string | null;
    listen_addrs: [string, number][];
    type: string;
    wireguard_conf?: string;
}

export interface BackendState {
    available: boolean;
    version: string;
    contentViews: string[];
    servers: ServerInfo[];
}

export const defaultState: BackendState = {
    available: false,
    version: "",
    contentViews: [],
    servers: [],
};

export function mockUpdate(newState: Partial<BackendState>) {
    return {
        type: UPDATE,
        data: newState,
    };
}

export default function reducer(state = defaultState, action): BackendState {
    switch (action.type) {
        case RECEIVE:
        case UPDATE:
            return {
                ...state,
                available: true,
                ...action.data,
            };
        default:
            return state;
    }
}
