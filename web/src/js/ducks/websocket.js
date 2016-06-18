import { ConnectionActions } from '../actions.js'
import { AppDispatcher } from '../dispatcher.js'
import * as eventLogActions from './eventLog'
import * as flowActions from './flows'

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
            return { ...state, socket: action.socket }

        case CONNECTED:
            return { ...state, connected: true }

        case DISCONNECT:
            return { ...state, connected: false }

        case DISCONNECTED:
            return { ...state, socket: null }

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
        getState().settings.socket.close()
        dispatch({ type: DISCONNECT })
    }
}

export function onConnect() {
    // workaround to make sure that our state is already available.
    return dispatch => {
        dispatch({ type: CONNECTED })
        dispatch(flowActions.fetchFlows()).then(() => ConnectionActions.open())
    }
}

export function onDisconnect() {
    return dispatch => {
        ConnectionActions.close()
        dispatch(eventLogActions.addLogEntry('WebSocket connection closed.'))
        dispatch({ type: DISCONNECTED })
    }
}

export function onMessage(msg) {
    return dispatch => {
        const data = JSON.parse(msg.data)

        AppDispatcher.dispatchServerAction(data)

        switch (data.type) {

            case eventLogActions.UPDATE_LOG:
                return dispatch(eventLogActions.updateLogEntries(data))

            case flowActions.UPDATE_FLOWS:
                return dispatch(flowActions.updateFlows(data))

            default:
                console.warn('unknown message', data)
        }

        dispatch({ type: MESSAGE, msg })
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
