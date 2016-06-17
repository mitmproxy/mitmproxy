import { addLogEntry } from './eventLog'

export const WS_MSG_TYPE = 'settings'
export const WS_MSG_CMD_UPDATE = 'update'

export const BEGIN_FETCH = 'SETTINGS_BEGIN_FETCH'
export const FETCHED = 'SETTINGS_FETCHED'
export const RECV_WS_MSG = 'SETTINGS_RECV_WS_MSG'

const defaultState = { settings: {}, pendings: null }

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case BEGIN_FETCH:
            return { ...state, pendings: [] }

        case FETCHED:
            const pendings = state.pendings || []
            return { ...state, pendings: null, settings: pendings.reduce(reduceData, action.data) }

        case RECV_WS_MSG:
            if (state.pendings) {
                return { ...state, pendings: state.pendings.concat(action) }
            }
            return { ...state, settings: reduceData(state.settings, action) }

        default:
            return state
    }
}

function reduceData(data, action) {
    switch (action.cmd) {

        case WS_MSG_CMD_UPDATE:
            return { ...data, ...action.data }

        default:
            return data
    }
}

export function fetch() {
    return dispatch => {
        dispatch({ type: BEGIN_FETCH })
        return $.getJSON('/settings')
            .done(msg => dispatch(handleFetchResponse(msg.data)))
            .fail(error => dispatch(handleFetchError(error)));
    }
}

export function handleWsMsg(msg) {
    return { type: RECV_WS_MSG, cmd: msg.cmd, data: msg.data }
}

export function handleFetchResponse(data) {
    return { type: FETCHED, data }
}

export function handleFetchError(error) {
    // @todo let eventLog subscribe to SettingsActions.FETCH_ERROR
    return addLogEntry(error.stack || error.message || error)
}
