import reduceList, * as listActions from './utils/list'
import reduceView, * as viewActions from './utils/view'

export const ADD               = 'EVENTS_ADD'
export const RECEIVE           = 'EVENTS_RECEIVE'
export const TOGGLE_VISIBILITY = 'EVENTS_TOGGLE_VISIBILITY'
export const TOGGLE_FILTER     = 'EVENTS_TOGGLE_FILTER'
export const UNKNOWN_CMD       = 'EVENTS_UNKNOWN_CMD'
export const FETCH_ERROR       = 'EVENTS_FETCH_ERROR'

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
                view: reduceView(state.view, viewActions.updateFilter(state.list.data, log => filters[log.level])),
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
                list: reduceList(state.list, listActions.receive(action.events)),
                view: reduceView(state.view, viewActions.receive(action.events, log => state.filters[log.level])),
            }

        default:
            return state
    }
}

export function toggleFilter(filter) {
    return { type: TOGGLE_FILTER, filter }
}

export function toggleVisibility() {
    return { type: TOGGLE_VISIBILITY }
}

export function add(message, level = 'web') {
    return { type: ADD, message, level }
}
