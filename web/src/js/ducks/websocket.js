const CONNECTED = 'WEBSOCKET_CONNECTED'
const DISCONNECTED = 'WEBSOCKET_DISCONNECTED'

export const CMD_ADD = 'add'
export const CMD_UPDATE = 'update'
export const CMD_REMOVE = 'remove'
export const CMD_RESET = 'reset'

const defaultState = {
    connected: false,
    /* we may want to have an error message attribute here at some point */
}
export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case CONNECTED:
            return {
                connected: true
            }
        case DISCONNECTED:
            return {
                connected: false
            }
        default:
            return state
    }
}


export function connected() {
    return {type: CONNECTED}
}
export function disconnected() {
    return {type: DISCONNECTED}
}
