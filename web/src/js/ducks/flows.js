import { fetchApi as fetch } from '../utils'
import { CMD_RESET as WS_CMD_RESET } from './websocket'
import reduceList, * as listActions from './utils/list'

export const UPDATE_FILTER = 'FLOWS_UPDATE_FLOW_FILTER'
export const UPDATE_HIGHLIGHT = 'FLOWS_UPDATE_FLOW_HIGHLIGHT'
export const UPDATE_SORT = 'FLOWS_UPDATE_FLOW_SORT'
export const WS_MSG = 'FLOWS_WS_MSG'
export const SELECT = 'FLOWS_SELECT'
export const REQUEST_ACTION = 'FLOWS_REQUEST_ACTION'
export const REQUEST = 'FLOWS_REQUEST'
export const RECEIVE = 'FLOWS_RECEIVE'
export const FETCH_ERROR = 'FLOWS_FETCH_ERROR'

const defaultState = {
    selected: [],
    sorter: {},
    filter: null,
    highlight: null,
    list: reduceList(undefined, { type: Symbol('FLOWS_INIT_LIST') }),
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case UPDATE_FILTER:
            return {
                ...state,
                filter: action.filter,
                list: reduceList(state.list, listActions.updateFilter(makeFilterFun(action.filter))),
            }

        case UPDATE_HIGHLIGHT:
            return {
                ...state,
                highlight: action.highlight,
            }

        case UPDATE_SORTER:
            return {
                ...state,
                sorter: { column: action.column, desc: action.desc },
                list: reduceList(state.list, listActions.updateSorter(makeSortFun(action.sortKeyFun, action.desc))),
            }

        case SELECT:
            return {
                ...state,
                selected: [action.id],
            }

        case WS_MSG:
            return {
                ...state,
                list: reduceList(state.list, listActions.handleWsMsg(action.msg)),
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

function makeFilterFun(filter) {
    return filter ? Filt.parse(filter) : () => true
}

function makeSortFun(sortKeyFun, desc) {
    return (a, b) => {
        const ka = sortKeyFun(a)
        const kb = sortKeyFun(b)
        if (ka > kb) {
            return desc ? -1 : 1
        }
        if (ka < kb) {
            return desc ? 1 : -1
        }
        return 0
    }
}

/**
 * @public
 */
export function updateFilter(filter) {
    return { type: UPDATE_FILTER, filter }
}

/**
 * @public
 */
export function updateHighlight(highlight) {
    return { type: UPDATE_HIGHLIGHT, highlight }
}

/**
 * @public
 */
export  function updateSorter(column, desc, sortKeyFun) {
    return { type: UPDATE_SORTER, column, desc, sortKeyFun }
}

/**
 * @public
 */
export function selectFlow(id) {
    return (dispatch, getState) => {
        dispatch({ type: SELECT, currentSelection: getState().flows.selected[0], id })
    }
}

/**
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

        return fetch('/flows')
            .then(res => res.json())
            .then(json => dispatch(receive(json.data)))
            .catch(error => dispatch(fetchError(error)))
    }
}

/**
 * @public
 */
export function accept(flow) {
    fetch(`/flows/${flow.id}/accept`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function acceptAll() {
    fetch('/flows/accept', { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function delete(flow) {
    fetch(`/flows/${flow.id}`, { method: 'DELETE' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function duplicate(flow) {
    fetch(`/flows/${flow.id}/duplicate`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function replay(flow) {
    fetch(`/flows/${flow.id}/replay`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function revert(flow) {
    fetch(`/flows/${flow.id}/revert`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function update(flow, body) {
    fetch(`/flows/${flow.id}`, { method: 'PUT', body })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function clear() {
    fetch('/clear', { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function download() {
    window.location = '/flows/dump'
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function upload(file) {
    const body = new FormData()
    body.append('file', file)
    fetch('/flows/dump',  { method: 'post', body })
    return { type: REQUEST_ACTION }
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
