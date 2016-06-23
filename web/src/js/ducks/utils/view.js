import _ from 'lodash'

export const UPDATE_FILTER = 'VIEW_UPDATE_FILTER'
export const UPDATE_SORTER = 'VIEW_UPDATE_SORTER'
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
            const data = action.list.data.filter(action.filter).sort(action.sorter)
            return {
                ...state,
                data,
                indexOf: _.fromPairs(data.map((item, index) => [item.id, index])),
            }

        case UPDATE_SORTER:
            const data = state.data.slice().sort(action.sorter)
            return {
                ...state,
                data,
                indexOf: _.fromPairs(data.map((item, index) => [item.id, index]))
            }

        case ADD:
            if (!action.filter(action.item)) {
                return state
            }
            return {
                ...state,
                ...sortedInsert(state, action.item, action.sorter),
            }

        case REMOVE:
            return {
                ...state,
                ...sortedRemove(state, action.id),
            }

        case UPDATE:
            const nextState = {
                ...state,
                ...sortedRemove(state, action.id),
            }
            if (!action.filter(action.item)) {
                return nextState
            }
            return {
                ...nextState,
                ...sortedInsert(nextState, action.item, action.sorter)
            }

        case RECEIVE:
            const data = action.list.data.filter(action.filter).sort(action.sorter)
            return {
                ...state,
                data,
                indexOf: _.fromPairs(data.map((item, index) => [item.id, index])),
            }

        default:
            return state
    }
}

export function updateFilter(list, filter = defaultFilter, sorter = defaultSorter) {
    return { type: UPDATE_FILTER, list, filter, sorter }
}

export function updateSorter(sorter = defaultSorter) {
    return { type: UPDATE_SORTER, sorter }
}

export function add(item, filter = defaultFilter, sorter = defaultSorter) {
    return { type: ADD, item, filter, sorter }
}

export function update(id, item, filter = defaultFilter, sorter = defaultSorter) {
    return { type: UPDATE, id, item, filter, sorter }
}

export function remove(id) {
    return { type: REMOVE, id }
}

export function receive(list, filter = defaultFilter, sorter = defaultSorter) {
    return { type: RECEIVE, list, filter, sorter }
}

function sortedInsert(state, item, sorter) {
    const index = sortedIndex(state.data, item, sorter)
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

function sortedIndex(list, item, sorter) {
    let low = 0
    let high = list.length

    while (low < high) {
        const middle = (low + high) >>> 1
        if (sorter(item, list[middle]) > 0) {
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

function defaultSorter(a, b) {
    return 0
}
