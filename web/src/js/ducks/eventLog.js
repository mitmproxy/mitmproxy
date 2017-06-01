import reduceStore from "./utils/store"
import * as storeActions from "./utils/store"

export const ADD               = 'EVENTS_ADD'
export const RECEIVE           = 'EVENTS_RECEIVE'
export const TOGGLE_VISIBILITY = 'EVENTS_TOGGLE_VISIBILITY'
export const TOGGLE_FILTER     = 'EVENTS_TOGGLE_FILTER'

const defaultState = {
    visible: false,
    filters: { debug: false, info: true, web: true, warn: true, error: true },
    ...reduceStore(undefined, {}),
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
                ...reduceStore(state, storeActions.setFilter(log => filters[log.level]))
            }

        case ADD:
        case RECEIVE:
            return {
                ...state,
                ...reduceStore(state, storeActions[action.cmd](action.data, log => state.filters[log.level]))
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
    let data = {
        id: Math.random().toString(),
        message,
        level,
    }
    return {
        type: ADD,
        cmd: "add",
        data
    }
}
