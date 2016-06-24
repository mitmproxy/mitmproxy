import { ConnectionActions } from '../actions.js'
import { AppDispatcher } from '../dispatcher.js'
import * as eventLogActions from './eventLog'
import * as flowsActions from './flows'
import * as settingsActions from './settings'

export const CMD_ADD = 'add'
export const CMD_UPDATE = 'update'
export const CMD_REMOVE = 'remove'
export const CMD_RESET = 'reset'

export const SYM_SOCKET = Symbol('WEBSOCKET_SYM_SOCKET')

export const CONNECT = 'WEBSOCKET_CONNECT'
export const CONNECTED = 'WEBSOCKET_CONNECTED'
export const DISCONNECT = 'WEBSOCKET_DISCONNECT'
export const DISCONNECTED = 'WEBSOCKET_DISCONNECTED'
export const ERROR = 'WEBSOCKET_ERROR'
export const MESSAGE = 'WEBSOCKET_MESSAGE'

/* we may want to have an error message attribute here at some point */
const defaultState = { connected: false, socket: null }

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case CONNECT:
            return { ...state, [SYM_SOCKET]: action.socket }

        case CONNECTED:
            return { ...state, connected: true }

        case DISCONNECT:
            return { ...state, connected: false }

        case DISCONNECTED:
            return { ...state, [SYM_SOCKET]: null, connected: false }

        default:
            return state
    }
}

export function connect() {
    return dispatch => {
        const socket = new WebSocket(location.origin.replace('http', 'ws') + '/updates')

        // @todo remove this
        window.ws = socket

        socket.addEventListener('open', () => dispatch(onConnect()))
        socket.addEventListener('close', () => dispatch(onDisconnect()))
        socket.addEventListener('message', msg => dispatch(onMessage(msg)))
        socket.addEventListener('error', error => dispatch(onError(error)))

        dispatch({ type: CONNECT, socket })

        return socket
    }
}

export function disconnect() {
    return (dispatch, getState) => {
        getState().settings[SYM_SOCKET].close()
        dispatch({ type: DISCONNECT })
    }
}

export function onConnect() {
    // workaround to make sure that our state is already available.
    return dispatch => {
        dispatch({ type: CONNECTED })
        dispatch(settingsActions.fetchSettings())
        dispatch(flowsActions.fetchFlows()).then(() => ConnectionActions.open())
    }
}

export function onMessage(msg) {
    return dispatch => {
        const data = JSON.parse(msg.data)

        AppDispatcher.dispatchServerAction(data)

        switch (data.type) {

            case eventLogActions.WS_MSG_TYPE:
                return dispatch(eventLogActions.handleWsMsg(data))

            case flowsActions.WS_MSG_TYPE:
                return dispatch(flowsActions.handleWsMsg(data))

            case settingsActions.UPDATE_SETTINGS:
                return dispatch(settingsActions.handleWsMsg(data))

            default:
                console.warn('unknown message', data)
        }

        dispatch({ type: MESSAGE, msg })
    }
}

export function onDisconnect() {
    return dispatch => {
        ConnectionActions.close()
        dispatch(eventLogActions.addLogEntry('WebSocket connection closed.'))
        dispatch({ type: DISCONNECTED })
    }
}

export function onError(error) {
    // @todo let event log subscribe WebSocketActions.ERROR
    return dispatch => {
        ConnectionActions.error()
        dispatch(eventLogActions.addLogEntry('WebSocket connection error.'))
        dispatch({ type: ERROR, error })
    }
}
