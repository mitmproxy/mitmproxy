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
    // need to adjust sortedIndexOf as well
    // if (sortFn.reverse)
    //    return (a, b) => compareFn(b, a)
    return compareFn
}

const sortedInsert = (list, sortFn, item) => {
    let l = [...list, item]
    l.indexOf = x => sortedIndexOf(l, x, sortFn)
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
    let l = list.filter(x => x.id !== itemId)
    l.indexOf = x => sortedIndexOf(l, x, sortFn)
    return l
}

export function sortedIndexOf(list, value, sortFn) {
    if (!sortFn) {
        sortFn = x => 0 // This triggers the linear search for flows that have the same sort value.
    }

    let low = 0,
        high = list.length,
        val = sortFn(value),
        mid;
    while (low < high) {
        mid = (low + high) >>> 1;
        if (sortFn(list[mid]) < val) {
            low = mid + 1
        } else {
            high = mid
        }
    }

    // Two flows may have the same sort value.
    // we previously determined the leftmost flow with the same sort value,
    // so no we need to scan linearly
    while (list[low].id !== value.id && sortFn(list[low + 1]) === val) {
        low++
    }
    return low;
}

// for when the list changes
export function updateViewList(currentView, currentList, nextList, action, filterFn = defaultFilterFn, sortFn = defaultSortFn) {
    switch (action.cmd) {
        case REQUEST_LIST:
            return currentView
        case RECEIVE_LIST:
            return updateViewFilter(nextList, filterFn, sortFn)
        case ADD:
            if (filterFn(action.item)) {
                return sortedInsert(currentView, sortFn, action.item)
            }
            return currentView
        case UPDATE:
            // let's determine if it's in the view currently and if it should be in the view.
            let currentItemState = currentList.byId[action.item.id],
                nextItemState = action.item,
                isInView = filterFn(currentItemState),
                shouldBeInView = filterFn(nextItemState)

            if (!isInView && shouldBeInView)
                return sortedInsert(currentView, sortFn, action.item)
            if (isInView && !shouldBeInView)
                return sortedRemove(currentView, sortFn, action.item)
            if (isInView && shouldBeInView) {
                let s = [...currentView]
                s.indexOf = x => sortedIndexOf(s, x, sortFn)
                s[s.indexOf(currentItemState)] = nextItemState
                if (sortFn && sortFn(currentItemState) !== sortFn(nextItemState))
                    s.sort(makeCompareFn(sortFn))
                return s
            }
            return currentView
        case REMOVE:
            let isInView_ = filterFn(currentList.byId[action.item.id])
            if (isInView_) {
                return sortedRemove(currentView, sortFn, action.item)
            }
            return currentView
        default:
            console.error("Unknown list action: ", action)
            return currentView
    }
}

export function updateViewFilter(list, filterFn = defaultFilterFn, sortFn = defaultSortFn) {
    let filtered = list.list.filter(filterFn)
    if (sortFn){
        filtered.sort(makeCompareFn(sortFn))
    }
    filtered.indexOf = x => sortedIndexOf(filtered, x, sortFn)

    return filtered
}

export function updateViewSort(list, sortFn = defaultSortFn) {
    let sorted = [...list]
    if (sortFn) {
        sorted.sort(makeCompareFn(sortFn))
    }
    sorted.indexOf = x => sortedIndexOf(sorted, x, sortFn)

    return sorted
}
