export enum ConnectionState {
    INIT = "CONNECTION_INIT",
    FETCHING = "CONNECTION_FETCHING", // WebSocket is established, but still fetching resources.
    ESTABLISHED = "CONNECTION_ESTABLISHED",
    ERROR = "CONNECTION_ERROR",
    OFFLINE = "CONNECTION_OFFLINE", // indicates that there is no live (websocket) backend.
}

interface ConnState {
    state: ConnectionState;
    message?: string;
}

const defaultState: ConnState = {
    state: ConnectionState.INIT,
    message: undefined,
};

export default function reducer(state = defaultState, action): ConnState {
    switch (action.type) {
        case ConnectionState.ESTABLISHED:
        case ConnectionState.FETCHING:
        case ConnectionState.ERROR:
        case ConnectionState.OFFLINE:
            return {
                state: action.type,
                message: action.message,
            };

        default:
            return state;
    }
}

export function startFetching() {
    return { type: ConnectionState.FETCHING };
}

export function connectionEstablished() {
    return { type: ConnectionState.ESTABLISHED };
}

export function connectionError(message) {
    return { type: ConnectionState.ERROR, message };
}

export function setOffline() {
    return { type: ConnectionState.OFFLINE };
}
