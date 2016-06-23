import { fetchApi as fetch } from '../utils'
import { CMD_RESET as WS_CMD_RESET } from './websocket'
import reduceList, * as listActions from './utils/list'

export const WS_MSG_TYPE = 'UPDATE_LOG'

export const TOGGLE_VISIBILITY = 'EVENTLOG_TOGGLE_VISIBILITY'
export const TOGGLE_FILTER = 'EVENTLOG_TOGGLE_FILTER'
export const ADD = 'EVENTLOG_ADD'
export const WS_MSG = 'EVENTLOG_WS_MSG'
export const REQUEST = 'EVENTLOG_REQUEST'
export const RECEIVE = 'EVENTLOG_RECEIVE'
export const FETCH_ERROR = 'EVENTLOG_FETCH_ERROR'

const defaultState = {
    logId: 0,
    visible: false,
    filters: { debug: false, info: true, web: true },
    list: reduceList(undefined, { type: Symbol('EVENTLOG_INIT_LIST') }),
    view: reduceView(undefined, viewActions.init([]))
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case TOGGLE_VISIBILITY:
            return { ...state, visible: !state.visible }

        case TOGGLE_FILTER:
            const filters = { ...state.filters, [action.filter]: !state.filters[action.filter] }
            return {
                ...state,
                filters,
                view: reduceView(state.list, listActions.updateFilter(e => filters[e.level], state.list))
            }

        case ADD:
            return {
                ...state,
                logId: state.logId + 1,
                list: reduceList(state.list, listActions.add({
                    id: `log-${state.logId}`,
                    message: action.message,
                    level: action.level,
                }))
            }

        case WS_MSG:
            return {
                ...state,
                list: reduceList(state.list, listActions.handleWsMsg(action.msg))
            }

        case REQUEST:
            return {
                ...state,
                list: reduceList(state.list, listActions.request())
            }

        case RECEIVE:
            return {
                ...state,
                list: reduceList(state.list, listActions.receive(action.list))
            }

        default:
            return state
    }
}

/**
 * @public
 */
export function toggleFilter(filter) {
    return { type: TOGGLE_FILTER, filter }
}

/**
 * @public
 *
 * @todo move to ui?
 */
export function toggleVisibility() {
    return { type: TOGGLE_VISIBILITY }
}

/**
 * @public
 */
export function add(message, level = 'web') {
    return { type: ADD, message, level }
}

/**
 * This action creater takes all WebSocket events
 *
 * @public websocket
 */
export function handleWsMsg(msg) {
    if (msg.cmd === WS_CMD_RESET) {
        return fetchData()
    }
    return { type: WS_MSG, msg }
}

/**
 * @public websocket
 */
export function fetchData() {
    return dispatch => {
        dispatch(request())

        return fetch('/events')
            .then(res => res.json())
            .then(json =>  dispatch(receive(json.data)))
            .catch(error => dispatch(fetchError(error)))
    }
}

/**
 * @private
 */
export function request() {
    return { type: REQUEST }
}

/**
 * @private
 */
export function receive(list) {
    return { type: RECEIVE, list }
}

/**
 * @private
 */
export function fetchError(error) {
    return { type: FETCH_ERROR, error }
}
