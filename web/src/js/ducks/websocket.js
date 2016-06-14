const CONNECTED = 'WEBSOCKET_CONNECTED'
const DISCONNECTED = 'WEBSOCKET_DISCONNECTED'


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
