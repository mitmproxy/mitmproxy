import { fetchApi } from '../utils'
import reduceList, * as listActions from './utils/list'
import reduceView, * as viewActions from './utils/view'
import * as websocketActions from './websocket'

export const WS_MSG_TYPE = 'UPDATE_LOG'

export const TOGGLE_VISIBILITY = 'EVENTLOG_TOGGLE_VISIBILITY'
export const TOGGLE_FILTER = 'EVENTLOG_TOGGLE_FILTER'
export const ADD = 'EVENTLOG_ADD'
export const WS_MSG = 'EVENTLOG_WS_MSG'
export const REQUEST = 'EVENTLOG_REQUEST'
export const RECEIVE = 'EVENTLOG_RECEIVE'
export const FETCH_ERROR = 'EVENTLOG_FETCH_ERROR'
export const UNKNOWN_CMD = 'EVENTLOG_UNKNOWN_CMD'

const defaultState = {
    logId: 0,
    visible: false,
    filters: { debug: false, info: true, web: true },
    list: null,
    view: null,
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
                view: reduceView(state.view, viewActions.updateFilter(state.list, log => filters[log.level])),
            }

        case ADD:
            const item = {
                id: `log-${state.logId}`,
                message: action.message,
                level: action.level,
            }
            return {
                ...state,
                logId: state.logId + 1,
                list: reduceList(state.list, listActions.add(item)),
                view: reduceView(state.view, viewActions.add(item, log => state.filters[log.level])),
            }

        case REQUEST:
            return {
                ...state,
                list: reduceList(state.list, listActions.request()),
            }

        case RECEIVE:
            return {
                ...state,
                list: reduceList(state.list, listActions.receive(action.list)),
            }

        default:
            return {
                ...state,
                list: reduceList(state.list, action),
            }
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
    switch (msg.cmd) {

        case websocketActions.CMD_ADD:
            return add(msg.data.message, msg.data.level)

        case websocketActions.CMD_RESET:
            return fetchData()

        default:
            return { type: UNKNOWN_CMD, msg }
    }
}

/**
 * @public websocket
 */
export function fetchData() {
    return dispatch => {
        dispatch(request())

        return fetchApi('/events')
            .then(res => res.json())
            .then(json => dispatch(receive(json.data)))
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
