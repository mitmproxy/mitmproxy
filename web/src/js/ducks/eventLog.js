import reduceList, * as listActions from './utils/list'
import reduceView, * as viewActions from './utils/view'
import * as websocketActions from './websocket'
import * as msgQueueActions from './msgQueue'

export const MSG_TYPE = 'UPDATE_EVENTLOG'
export const DATA_URL = '/events'

export const ADD               = 'EVENTLOG_ADD'
export const RECEIVE           = 'EVENTLOG_RECEIVE'
export const TOGGLE_VISIBILITY = 'EVENTLOG_TOGGLE_VISIBILITY'
export const TOGGLE_FILTER     = 'EVENTLOG_TOGGLE_FILTER'
export const UNKNOWN_CMD       = 'EVENTLOG_UNKNOWN_CMD'
export const FETCH_ERROR       = 'EVENTLOG_FETCH_ERROR'

const defaultState = {
    logId: 0,
    visible: false,
    filters: { debug: false, info: true, web: true },
    list: reduceList(undefined, {}),
    view: reduceView(undefined, {}),
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case TOGGLE_VISIBILITY:
            return {
                ...state,
                visible: !state.visible
            }

        case TOGGLE_FILTER:
            const filters = { ...state.filters, [action.filter]: !state.filters[action.filter] }
            return {
                ...state,
                filters,
                view: reduceView(state.view, viewActions.updateFilter(state.list, log => filters[log.level])),
            }

        case ADD:
            const item = {
                id: state.logId,
                message: action.message,
                level: action.level,
            }
            return {
                ...state,
                logId: state.logId + 1,
                list: reduceList(state.list, listActions.add(item)),
                view: reduceView(state.view, viewActions.add(item, log => state.filters[log.level])),
            }

        case RECEIVE:
            return {
                ...state,
                list: reduceList(state.list, listActions.receive(action.list)),
                view: reduceView(state.view, viewActions.receive(list, log => state.filters[log.level])),
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
    return msgQueueActions.fetchData(MSG_TYPE)
}

/**
 * @public msgQueue
 */
export function receiveData(list) {
    return { type: RECEIVE, list }
}
