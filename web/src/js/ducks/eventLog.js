import { fetchApi as fetch } from '../utils'
import reduceList, * as listActions from './utils/list'

export const TOGGLE_FILTER = 'EVENTLOG_TOGGLE_FILTER'
export const TOGGLE_VISIBILITY = 'EVENTLOG_TOGGLE_VISIBILITY'
export const ADD = 'EVENTLOG_ADD'
export const UPDATE = 'EVENTLOG_UPDATE'
export const REQUEST = 'EVENTLOG_REQUEST'
export const RECEIVE = 'EVENTLOG_RECEIVE'
export const ERROR = 'EVENTLOG_ERROR'

const defaultState = {
    visible: false,
    filters: { debug: false, info: true, web: true },
    list: reduceList(undefined, { type: Symbol('EVENTLOG_INIT_LIST') })
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
                list: reduceList(state.list, listActions.updateFilter(e => filters[e.level]))
            }

        case ADD:
            return {
                ...state,
                list: reduceList(state.list, listActions.add({ message: action.message, level: action.level }))
            }

        case UPDATE:
            return {
                ...state,
                list: reduceList(state.list, listActions.update(action))
            }

        case RECEIVE:
            return {
                ...state,
                list: reduceList(state.list, listActions.reset(action.list))
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
        return fetch()
    }
    return update(msg.cmd, msg.data)
}

/**
 * @private
 */
export function update(cmd, data) {
    return { type: UPDATE, cmd, data }
}

/**
 * @private
 */
export function fetch() {
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
