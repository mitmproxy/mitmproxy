import reduceView, * as viewActions from './utils/view'
import * as flowActions from './flows'
import Filt from '../filt/filt'
import { RequestUtils } from '../flow/utils'

export const UPDATE_FILTER = 'FLOWVIEW_UPDATE_FILTER'
export const UPDATE_SORT = 'FLOWVIEW_UPDATE_SORT'
export const UPDATE_HIGHLIGHT = 'FLOWVIEW_UPDATE_HIGHLIGHT'


const sortKeyFuns = {

    TLSColumn: flow => flow.request.scheme,

    PathColumn: flow => RequestUtils.pretty_url(flow.request),

    MethodColumn: flow => flow.request.method,

    StatusColumn: flow => flow.response && flow.response.status_code,

    TimeColumn: flow => flow.response && flow.response.timestamp_end - flow.request.timestamp_start,

    SizeColumn: flow => {
        let total = flow.request.contentLength
        if (flow.response) {
            total += flow.response.contentLength || 0
        }
        return total
    },
}

export function makeFilter(filter) {
    if (!filter) {
        return
    }
    return Filt.parse(filter)
}

export function makeSort({ column, desc }) {
    const sortKeyFun = sortKeyFuns[column]
    if (!sortKeyFun) {
        return
    }
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


const defaultState = {
    highlight: null,
    filter: null,
    sort: { column: null, desc: false },
    ...reduceView(undefined, {})
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case UPDATE_HIGHLIGHT:
            return {
                ...state,
                highlight: action.highlight,
            }

        case UPDATE_FILTER:
            return {
                ...reduceView(
                    state,
                    viewActions.updateFilter(
                        action.flows,
                        makeFilter(action.filter),
                        makeSort(state.sort)
                    )
                ),
                filter: action.filter,
            }

        case UPDATE_SORT:
            const sort = { column: action.column, desc: action.desc }
            return {
                ...reduceView(
                    state,
                    viewActions.updateSort(
                        makeSort(sort)
                    )
                ),
                sort,
            }

        case flowActions.ADD:
            return {
                ...reduceView(
                    state,
                    viewActions.add(
                        action.item,
                        makeFilter(state.filter),
                        makeSort(state.sort)
                    )
                ),
            }

        case flowActions.UPDATE:
            return {
                ...reduceView(
                    state,
                    viewActions.update(
                        action.item,
                        makeFilter(state.filter),
                        makeSort(state.sort)
                    )
                ),
            }

        case flowActions.REMOVE:
            /* FIXME: Implement select switch on remove
                return (dispatch, getState) => {
                    let currentIndex = getState().flowView.indexOf[getState().flows.selected[0]]
                    let maxIndex = getState().flowView.data.length - 1
                    let deleteLastEntry = maxIndex == 0
                    if (deleteLastEntry)
                        dispatch(select())
                    else
                        dispatch(selectRelative(currentIndex == maxIndex ? -1 : 1) )
             */
            return {
                ...reduceView(
                    state,
                    viewActions.remove(
                        action.id
                    )
                ),
            }

        case flowActions.RECEIVE:
            return {
                ...reduceView(
                    state,
                    viewActions.receive(
                        action.flows,
                        makeFilter(state.filter),
                        makeSort(state.sort)
                    )
                ),
            }

        default:
            return {
                ...reduceView(state, action),
            }
    }
}

export function updateFilter(filter) {
    return (dispatch, getState) => {
        dispatch({ type: UPDATE_FILTER, filter, flows: getState().flows.data })
    }
}

export function updateHighlight(highlight) {
    return { type: UPDATE_HIGHLIGHT, highlight }
}

export function updateSort(column, desc) {
    return { type: UPDATE_SORT, column, desc }
}

export function selectRelative(shift) {
    return (dispatch, getState) => {
        let currentSelectionIndex = getState().flowView.indexOf[getState().flows.selected[0]]
        let minIndex = 0
        let maxIndex = getState().flowView.data.length - 1
        let newIndex
        if (currentSelectionIndex === undefined) {
            newIndex = (shift < 0) ? minIndex : maxIndex
        } else {
            newIndex = currentSelectionIndex + shift
            newIndex = Math.max(newIndex, minIndex)
            newIndex = Math.min(newIndex, maxIndex)
        }
        let flow = getState().flowView.data[newIndex]
        dispatch(flowActions.select(flow ? flow.id : undefined))
    }
}
