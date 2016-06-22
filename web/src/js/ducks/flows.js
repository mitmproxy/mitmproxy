import { fetchApi as fetch } from '../utils'
import { CMD_RESET as WS_CMD_RESET } from './websocket'
import reduceList, * as listActions from './utils/list'

export const WS_MSG = 'FLOWS_WS_MSG'
export const UPDATE_FILTER = 'FLOWS_UPDATE_FLOW_FILTER'
export const UPDATE_HIGHLIGHT = 'FLOWS_UPDATE_FLOW_HIGHLIGHT'
export const UPDATE_SORT = 'FLOWS_UPDATE_FLOW_SORT'
export const SELECT = 'FLOWS_SELECT'

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
                list: reduceList(state.list, listActions.updateFilter(action.filter ? Filt.parse(action.filter) : () => true)),
            }

        case UPDATE_HIGHLIGHT:
            return {
                ...state,
                highlight: action.highlight,
            }

        case UPDATE_SORTER:
            const { column, desc, sortKeyFun } = action
            return {
                ...state,
                sorter: { column, desc },
                list: reduceList(state.list, listActions.updateSorter((a, b) => {
                    const ka = sortKeyFun(a)
                    const kb = sortKeyFun(b)
                    if (ka > kb) {
                        return desc ? -1 : 1
                    }
                    if (ka < kb) {
                        return desc ? 1 : -1
                    }
                    return 0
                })),
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

        default:
            return state
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
    return { type: SET_SORTER, column, desc, sortKeyFun }
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
