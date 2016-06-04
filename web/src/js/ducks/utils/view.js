import {ADD, UPDATE, REMOVE, REQUEST_LIST, RECEIVE_LIST} from "./list"

const defaultFilterFn = x => true
const defaultSortFn = false

const makeCompareFn = sortFn => {
    let compareFn = (a, b) => {
        let akey = sortFn(a),
            bkey = sortFn(b)
        if (akey < bkey) {
            return -1
        } else if (akey > bkey) {
            return 1
        } else {
            return 0
        }
    }
    if (sortFn.reverse)
        return (a, b) => compareFn(b, a)
    return compareFn
}

const sortedInsert = (list, sortFn, item) => {
    let l = [...list, item]
    let compareFn = makeCompareFn(sortFn)

    // only sort if sorting order is not correct yet
    if (sortFn && compareFn(list[list.length - 1], item) > 0) {
        // TODO: This is untested
        console.debug("sorting view...")
        l.sort(compareFn)
    }
    return l
}

const sortedRemove = (list, sortFn, item) => {
    let itemId = item.id
    return list.filter(x => x.id !== itemId)
}

// for when the list changes
export function updateViewList(state, currentList, nextList, action, filterFn = defaultFilterFn, sortFn = defaultSortFn) {
    switch (action.cmd) {
        case REQUEST_LIST:
            return state
        case RECEIVE_LIST:
            return updateViewFilter(nextList.list, filterFn, sortFn)
        case ADD:
            if (filterFn(action.item)) {
                return sortedInsert(state, sortFn, action.item)
            }
            return state
        case UPDATE:
            // let's determine if it's in the view currently and if it should be in the view.
            let currentItemState = currentList.byId[action.item.id],
                nextItemState = action.item,
                isInView = filterFn(currentItemState),
                shouldBeInView = filterFn(nextItemState)

            if (!isInView && shouldBeInView)
                return sortedInsert(state, sortFn, action.item)
            if (isInView && !shouldBeInView)
                return sortedRemove(state, sortFn, action.item)
            if (isInView && shouldBeInView && sortFn(currentItemState) !== sortFn(nextItemState)) {
                let s = [...state]
                s.sort(sortFn)
                return s
            }
            return state
        case REMOVE:
            let isInView_ = filterFn(currentList.byId[action.item.id])
            if (isInView_) {
                return sortedRemove(state, sortFn, action.item)
            }
            return state
        default:
            console.error("Unknown list action: ", action)
            return state
    }
}

export function updateViewFilter(list, filterFn = defaultFilterFn, sortFn = defaultSortFn) {
    let filtered = list.filter(filterFn)
    if (sortFn)
        filtered.sort(makeCompareFn(sortFn))
    return filtered
}