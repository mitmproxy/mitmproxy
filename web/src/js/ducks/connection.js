export const ConnectionState = {
    INIT: Symbol("init"),
    FETCHING: Symbol("fetching"), // WebSocket is established, but still fetching resources.
    ESTABLISHED: Symbol("established"),
    ERROR: Symbol("error"),
    OFFLINE: Symbol("offline"), // indicates that there is no live (websocket) backend.
}

const defaultState = {
    state: ConnectionState.INIT,
    message: null,
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case ConnectionState.ESTABLISHED:
        case ConnectionState.FETCHING:
        case ConnectionState.ERROR:
        case ConnectionState.OFFLINE:
            return {
                state: action.type,
                message: action.message
            }

        default:
            return state
    }
}

export function startFetching() {
    return { type: ConnectionState.FETCHING }
}

export function connectionEstablished() {
    return { type: ConnectionState.ESTABLISHED }
}

export function connectionError(message) {
    return { type: ConnectionState.ERROR, message }
}
export function setOffline() {
    return { type: ConnectionState.OFFLINE }
}
