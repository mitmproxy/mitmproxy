import stable from 'stable'

export const SET_FILTER = 'LIST_SET_FILTER'
export const SET_SORT = 'LIST_SET_SORT'
export const ADD = 'LIST_ADD'
export const UPDATE = 'LIST_UPDATE'
export const REMOVE = 'LIST_REMOVE'
export const RECEIVE = 'LIST_RECEIVE'

const defaultState = {
    byId: {},
    list: [],
    listIndex: {},
    view: [],
    viewIndex: {},
}

/**
 * The store reducer can be used as a mixin to another reducer that always returns a
 * new { byId, list, listIndex, view, viewIndex } object. The reducer using the store
 * usually has to map its action to the matching store action and then call the mixin with that.
 *
 * Example Usage:
 *
 *      import reduceStore, * as storeActions from "./utils/store"
 *
 *      case EVENTLOG_ADD:
 *          return {
 *              ...state,
 *              ...reduceStore(state, storeActions.add(action.data))
 *          }
 *
 */
export default function reduce(state = defaultState, action) {

    let { byId, list, listIndex, view, viewIndex } = state

    switch (action.type) {
        case SET_FILTER:
            view = stable(list.filter(action.filter), action.sort)
            viewIndex = {}
            view.forEach((item, index) => {
                viewIndex[item.id] = index
            })
            break

        case SET_SORT:
            view = stable([...view], action.sort)
            viewIndex = {}
            view.forEach((item, index) => {
                viewIndex[item.id] = index
            })
            break

        case ADD:
            if (action.item.id in byId) {
                // we already had that.
                break
            }
            byId = { ...byId, [action.item.id]: action.item }
            listIndex = { ...listIndex, [action.item.id]: list.length }
            list = [...list, action.item]
            if (action.filter(action.item)) {
                ({ view, viewIndex } = sortedInsert(state, action.item, action.sort))
            }
            break

        case UPDATE:
            byId = { ...byId, [action.item.id]: action.item }
            list = [...list]
            list[listIndex[action.item.id]] = action.item

            let hasOldItem = action.item.id in viewIndex
            let hasNewItem = action.filter(action.item)
            if (hasNewItem && !hasOldItem) {
                ({view, viewIndex} = sortedInsert(state, action.item, action.sort))
            }
            else if (!hasNewItem && hasOldItem) {
                ({data: view, dataIndex: viewIndex} = removeData(view, viewIndex, action.item.id))
            }
            else if (hasNewItem && hasOldItem) {
                ({view, viewIndex} = sortedUpdate(state, action.item, action.sort))
            }
            break

        case REMOVE:
            if (!(action.id in byId)) {
                break
            }
            byId = {...byId}
            delete byId[action.id];
            ({data: list, dataIndex: listIndex} = removeData(list, listIndex, action.id))

            if (action.id in viewIndex) {
                ({data: view, dataIndex: viewIndex} = removeData(view, viewIndex, action.id))
            }
            break

        case RECEIVE:
            list = action.list
            listIndex = {}
            byId = {}
            list.forEach((item, i) => {
                byId[item.id] = item
                listIndex[item.id] = i
            })
            view = list.filter(action.filter).sort(action.sort)
            viewIndex = {}
            view.forEach((item, index) => {
                viewIndex[item.id] = index
            })
            break
    }
    return { byId, list, listIndex, view, viewIndex }
}


export function setFilter(filter = defaultFilter, sort = defaultSort) {
    return { type: SET_FILTER, filter, sort }
}

export function setSort(sort = defaultSort) {
    return { type: SET_SORT, sort }
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
    const index = sortedIndex(state.view, item, sort)
    const view = [...state.view]
    const viewIndex = { ...state.viewIndex }

    view.splice(index, 0, item)
    for (let i = view.length - 1; i >= index; i--) {
        viewIndex[view[i].id] = i
    }

    return { view, viewIndex }
}

function removeData(currentData, currentDataIndex, id) {
    const index = currentDataIndex[id]
    const data = [...currentData]
    const dataIndex = { ...currentDataIndex }
    delete dataIndex[id];

    data.splice(index, 1)
    for (let i = data.length - 1; i >= index; i--) {
        dataIndex[data[i].id] = i
    }

    return { data, dataIndex }
}

function sortedUpdate(state, item, sort) {
    let view = [...state.view]
    let viewIndex = { ...state.viewIndex }
    let index = viewIndex[item.id]
    view[index] = item
    while (index + 1 < view.length && sort(view[index], view[index + 1]) > 0) {
        view[index] = view[index + 1]
        view[index + 1] = item
        viewIndex[item.id] = index + 1
        viewIndex[view[index].id] = index
        ++index
    }
    while (index > 0 && sort(view[index], view[index - 1]) < 0) {
        view[index] = view[index - 1]
        view[index - 1] = item
        viewIndex[item.id] = index - 1
        viewIndex[view[index].id] = index
        --index
    }
    return { view, viewIndex }
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
