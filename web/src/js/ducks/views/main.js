import reduceView, * as viewActions from '../utils/list'
import * as viewsActions from '../views'

export const UPDATE_FILTER = 'FLOW_VIEWS_MAIN_UPDATE_FILTER'
export const UPDATE_SORTER = 'FLOW_VIEWS_MAIN_UPDATE_SORTER'
export const UPDATE_HIGHLIGHT = 'FLOW_VIEWS_MAIN_UPDATE_HIGHLIGHT'
export const SELECT = 'FLOW_VIEWS_MAIN_SELECT'

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

const defaultState = {
    highlight: null,
    selected: [],
    filter: null,
    sorter: { column: null, desc: false },
    view: undefined,
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case UPDATE_HIGHLIGHT:
            return {
                ...state,
                highlight: action.highlight,
            }

        case SELECT:
            return {
                ...state,
                selected: [action.id]
            }

        case UPDATE_FILTER:
            return {
                ...state,
                filter: action.filter,
                view: reduceView(
                    state.view,
                    viewActions.updateFilter(
                        action.list,
                        makeFilter(action.filter),
                        makeSorter(state.sorter)
                    )
                ),
            }

        case UPDATE_SORTER:
            const sorter = { column: action.column, desc: action.desc }
            return {
                ...state,
                sorter,
                view: reduceView(
                    state.view,
                    viewActions.updateSorter(
                        makeSorter(sorter)
                    )
                ),
            }

        case viewsActions.ADD:
            return {
                ...state,
                view: reduceView(
                    state.view,
                    viewActions.add(
                        action.item,
                        makeFilter(state.filter),
                        makeSorter(state.sorter)
                    )
                ),
            }

        case viewsActions.UPDATE:
            return {
                ...state,
                view: reduceView(
                    state.view,
                    viewActions.update(
                        action.id,
                        action.item,
                        makeFilter(state.filter),
                        makeSorter(state.sorter)
                    )
                ),
            }

        case viewsActions.REMOVE:
            return {
                ...state,
                view: reduceView(
                    state.view,
                    viewActions.remove(
                        action.id
                    )
                ),
            }

        case viewsActions.RECEIVE:
            return {
                ...state,
                view: reduceView(
                    state.view,
                    viewActions.receive(
                        action.list,
                        makeFilter(state.filter),
                        makeSorter(state.sorter)
                    )
                ),
            }

        default:
            return {
                ...state,
                view: reduceView(state.view, action)
            }
    }
}

/**
 * @public
 */
export function updateFilter(filter) {
    return (dispatch, getState) => {
        return { type: UPDATE_FILTER, filter, list: getState().flows.list }
    }
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
export function updateSorter(column, desc) {
    return { type: UPDATE_SORTER, column, desc }
}

/**
 * @public
 */
export function select(id) {
    return { type: SELECT, currentSelection: getState().flows.views.main.selected[0], id }
}

/**
 * @private
 */
function makeFilter(filter) {
    return filter && Filt.parse(filter)
}

/**
 * @private
 */
function makeSorter(column, desc) {
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
