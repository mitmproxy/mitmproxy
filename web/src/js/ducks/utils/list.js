import * as websocketActions from './websocket'

export const UPDATE_FILTER = 'LIST_UPDATE_FILTER'
export const UPDATE_SORTER = 'LIST_UPDATE_SORTER'
export const ADD = 'LIST_ADD'
export const UPDATE = 'LIST_UPDATE'
export const REMOVE = 'LIST_REMOVE'
export const UNKNOWN_CMD = 'LIST_UNKNOWN_CMD'
export const REQUEST = 'LIST_REQUEST'
export const RECEIVE = 'LIST_RECEIVE'
export const FETCH_ERROR = 'LIST_FETCH_ERROR'

export const SYM_FILTER = Symbol('LIST_SYM_FILTER')
export const SYM_SORTER = Symbol('LIST_SYM_SORTER')
export const SYM_PENDING = Symbol('LIST_SYM_PENDING')

// @todo add indexOf map if necessary
const defaultState = {
    raw: [],
    data: [],
    byId: {},
    isFetching: false,
    [SYM_FILTER]: () => true,
    [SYM_SORTER]: () => 0,
    [SYM_PENDING]: [],
}

export default function reduce(state = defaultState, action) {
    if (state.isFetching && action.type !== RECEIVE) {
        return {
            ...state,
            [SYM_PENDING]: [...state[SYM_PENDING], action]
        }
    }

    switch (action.type) {

        case UPDATE_FILTER:
            return {
                ...state,
                [SYM_FILTER]: action.filter,
                data: state.raw.filter(action.filter).sort(state[SYM_SORTER]),
            }

        case UPDATE_SORTER:
            return {
                ...state,
                [SYM_SORTER]: action.sorter,
                data: state.data.slice().sort(state[SYM_SORTER]),
            }

        case ADD:
            let data = state.data
            if (state[SYM_FILTER](action.item)) {
                data = [...state.data, action.item].sort(state[SYM_SORTER])
            }
            return {
                ...state,
                data,
                raw: [...state.raw, action.item],
                byId: { ...state.byId, [action.item.id]: action.item },
            }

        case UPDATE:
            // @todo optimize if necessary
            const raw = state.raw.map(item => item.id === action.id ? action.item : item)
            return {
                ...state,
                raw,
                data: raw.filter(state[SYM_FILTER]).sort(state[SYM_SORTER]),
                byId: { ...state.byId, [action.id]: null, [action.item.id]: action.item },
            }

        case REMOVE:
            // @todo optimize if necessary
            return {
                ...state,
                raw: state.raw.filter(item => item.id !== action.id),
                data: state.data.filter(item => item.id !== action.id),
                byId: { ...state.byId, [action.id]: null },
            }

        case REQUEST:
            return {
                ...state,
                isFetching: true,
            }

        case RECEIVE:
            return {
                ...state,
                isFetching: false,
                raw: action.list,
                data: action.list.filter(state[SYM_FILTER]).sort(state[SYM_SORTER]),
                byId: _.fromPairs(action.list.map(item => [item.id, item])),
            }

        default:
            return state
    }
}

export function updateFilter(filter) {
    return { type: UPDATE_FILTER, filter }
}

export function updateSorter(sorter) {
    return { type: UPDATE_SORTER, sorter }
}

export function add(item) {
    return { type: ADD, item }
}

export function update(id, item) {
    return { type: UPDATE, id, item }
}

export function remove(id) {
    return { type: REMOVE, id }
}

export function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_ADD:
            return add(msg.data)

        case websocketActions.CMD_UPDATE:
            return update(msg.data.id, msg.data)

        case websocketActions.CMD_REMOVE:
            return remove(msg.data.id)

        default:
            return { type: UNKNOWN_CMD, msg }
    }
}

export function request() {
    return { type: REQUEST }
}

export function receive(list) {
    return { type: RECEIVE, list }
}

export function fetchError(error) {
    return { type: FETCH_ERROR, error }
}
