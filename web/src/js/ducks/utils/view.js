import _ from 'lodash'

export const UPDATE_FILTER = 'VIEW_UPDATE_FILTER'
export const UPDATE_SORT = 'VIEW_UPDATE_SORT'
export const ADD = 'VIEW_ADD'
export const UPDATE = 'VIEW_UPDATE'
export const REMOVE = 'VIEW_REMOVE'
export const RECEIVE = 'VIEW_RECEIVE'

const defaultState = {
    data: [],
    indexOf: {},
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case UPDATE_FILTER:
        {
            const data = action.list.filter(action.filter).sort(action.sort)
            return {
                ...state,
                data,
                indexOf: _.fromPairs(data.map((item, index) => [item.id, index])),
            }
        }

        case UPDATE_SORT:
        {
            const data = [...state.data].sort(action.sort)
            return {
                ...state,
                data,
                indexOf: _.fromPairs(data.map((item, index) => [item.id, index])),
            }
        }

        case ADD:
            if (state.indexOf[action.item.id] != null || !action.filter(action.item)) {
                return state
            }
            return {
                ...state,
                ...sortedInsert(state, action.item, action.sort),
            }

        case REMOVE:
            if (state.indexOf[action.id] == null) {
                return state
            }
            return {
                ...state,
                ...sortedRemove(state, action.id),
            }

        case UPDATE:
            if (state.indexOf[action.item.id] == null) {
                return
            }
            const nextState = {
                ...state,
                ...sortedRemove(state, action.item.id),
            }
            if (!action.filter(action.item)) {
                return nextState
            }
            return {
                ...nextState,
                ...sortedInsert(nextState, action.item, action.sort)
            }

        case RECEIVE:
        {
            const data = action.list.filter(action.filter).sort(action.sort)
            return {
                ...state,
                data,
                indexOf: _.fromPairs(data.map((item, index) => [item.id, index])),
            }
        }

        default:
            return state
    }
}

export function updateFilter(list, filter = defaultFilter, sort = defaultSort) {
    return { type: UPDATE_FILTER, list, filter, sort }
}

export function updateSort(sort = defaultSort) {
    return { type: UPDATE_SORT, sort }
}

export function add(item, filter = defaultFilter, sort = defaultSort) {
    return { type: ADD, item, filter, sort }
}

export function update(item, filter = defaultFilter, sort = defaultSort) {
    return { type: UPDATE, item, filter, sort }
}

export function remove(id) {
    return { type: REMOVE, id }
}

export function receive(list, filter = defaultFilter, sort = defaultSort) {
    return { type: RECEIVE, list, filter, sort }
}

function sortedInsert(state, item, sort) {
    const index = sortedIndex(state.data, item, sort)
    const data = [...state.data]
    const indexOf = { ...state.indexOf }

    data.splice(index, 0, item)
    for (let i = data.length - 1; i >= index; i--) {
        indexOf[data[i].id] = i
    }

    return { data, indexOf }
}

function sortedRemove(state, id) {
    const index = state.indexOf[id]
    const data = [...state.data]
    const indexOf = { ...state.indexOf, [id]: null }

    data.splice(index, 1)
    for (let i = data.length - 1; i >= index; i--) {
        indexOf[data[i].id] = i
    }

    return { data, indexOf }
}

function sortedIndex(list, item, sort) {
    let low = 0
    let high = list.length

    while (low < high) {
        const middle = (low + high) >>> 1
        if (sort(item, list[middle]) >= 0) {
            low = middle + 1
        } else {
            high = middle
        }
    }

    return low
}

function defaultFilter() {
    return true
}

function defaultSort(a, b) {
    return 0
}
