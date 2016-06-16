import { StoreCmds } from '../actions'
import { addLogEntry } from './eventLog'

export const WS_MSG_TYPE = 'settings'
export const WS_MSG_CMD_RESET = 'reset'
export const WS_MSG_CMD_UPDATE = 'update'

export const BEGIN_FETCH = 'SETTINGS_BEGIN_FETCH'
export const FETCHED = 'SETTINGS_FETCHED'
export const RESET = 'SETTINGS_RESET'
export const FETCH_ERROR = 'SETTINGS_FETCH_ERROR'
export const RECV_WS_MSG = 'SETTINGS_RECV_WS_MSG'

const defaultState = { settings: {}, pendings: null, req: null }

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case BEGIN_FETCH:
            return { ...state, pendings: [], req: action.req }

        case FETCHED:
            const pendings = state.pendings || []
            return { ...state, pendings: null, settings: pendings.reduce(reduceData, action.data) }

        case RESET:
            return { ...state, pendings: null, settings: action.data || {} }

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

        case WS_MSG_CMD_RESET:
            return action.data || {}

        case WS_MSG_CMD_UPDATE:
            return _.merge({}, data, action.data)

        default:
            return data
    }
}

export function fetch() {
    return dispatch => {
        const req = $.getJSON('/settings')
            .done(msg => dispatch(handleFetchResponse(msg.data)))
            .fail(error => dispatch(handleFetchError(error)));

        dispatch({ type: BEGIN_FETCH, req })

        return req
    }
}

export function handleWsMsg(msg) {
    return (dispatch, getState) => {
        if (msg.cmd !== StoreCmds.RESET) {
            return dispatch({ type: RECV_WS_MSG, cmd: msg.cmd, data: msg.data })
        }
        const req = getState().settings.req
        if (req) {
            req.abort()
        }
        dispatch(reset(msg.data))
    }
}

export function handleFetchResponse(data) {
    return { type: FETCHED, data }
}

export function reset(data) {
    return { type: RESET, data }
}

export function handleFetchError(error) {
    return (dispatch, getState) => {
        dispatch(addLogEntry(error.stack || error.message || error))
        dispatch({ type: FETCH_ERROR, error })
    }
}
