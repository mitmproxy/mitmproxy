import { StoreCmds } from '../actions'

export const WS_MSG_TYPE = 'settings'
export const WS_MSG_CMD_RESET = 'reset'
export const WS_MSG_CMD_UPDATE = 'update'

export const BEGIN_FETCH = 'SETTINGS_BEGIN_FETCH'
export const FETCH_SETTINGS = 'SETTINGS_FETCH_SETTINGS'
export const FETCH_ERROR = 'SETTINGS_FETCH_ERROR'
export const RECV_WS_MSG = 'SETTINGS_RECV_WS_MSG'

const defaultState = { settings: {}, pendings: null, req: null }

function reduceData(data, action) {
    switch (action.cmd) {

        case WS_MSG_CMD_RESET:
            return action.data || {}

        case WS_MSG_CMD_UPDATE:
            return _.merge({}, data.settings, action.data)

        default:
            return data
    }
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case BEGIN_FETCH:
            return { ...state, pendings: [], req: action.req }

        case FETCH_SETTINGS:
            const pendings = state.pendings || []
            return { ...state, pendings: null, settings: pendings.reduce(reduceData, data) }

        case RECV_WS_MSG:
            if (state.pendings) {
                return { ...state, pendings: state.pendings.concat(action) }
            }
            return { ...state, settings: reduceData(state.settings, action) }

        default:
            return state
    }
}

export function fetch() {
    return dispatch => {
        const req = $.getJSON('/' + this.type)
            .done(msg => dispatch(reset(msg.data)))
            .fail(error => dispatch(handleFetchError(error)));

        dispatch({ type: BEGIN_FETCH, req })

        return req
    }
}

export function handleWsMsg(msg) {
    return (dispatch, getState) => {
        if (msg.cmd !== STORE_CMDS_RESET) {
            return dispatch({ type: RECV_WS_MSG, cmd: msg.cmd, data: msg.data })
        }
        const req = getState().settings.req
        if (req) {
            req.abort()
        }
        dispatch(reset(msg.data))
    }
}

export function reset(data) {
    return { type: FETCH_SETTINGS, data }
}

export function handleFetchError(error) {
    console.error(error)
    return { type: FETCH_ERROR, error }
}
