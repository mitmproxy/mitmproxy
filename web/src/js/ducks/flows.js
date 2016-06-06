import makeList from "./utils/list"
import Filt from "../filt/filt"
import {updateViewFilter, updateViewList} from "./utils/view"

export const UPDATE_FLOWS = "UPDATE_FLOWS"
export const SET_FILTER = "SET_FLOW_FILTER"
export const SET_HIGHLIGHT = "SET_FLOW_HIGHLIGHT"
export const SET_SORT = "SET_FLOW_SORT"
export const SELECT_FLOW = "SELECT_FLOW"

const {
    reduceList,
    updateList,
    fetchList,
} = makeList(UPDATE_FLOWS, "/flows")


const defaultState = {
    all: reduceList(),
    selected: [],
    view: [],
    filter: undefined,
    highlight: undefined,
    sort: {sortColumn: undefined, sortDesc: false},
}

function makeFilterFn(filter) {
    return filter ? Filt.parse(filter) : () => true;
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case UPDATE_FLOWS:
            let all = reduceList(state.all, action)
            return {
                ...state,
                all,
                view: updateViewList(state.view, state.all, all, action, makeFilterFn(action.filter))
            }
        case SET_FILTER:
            return {
                ...state,
                filter: action.filter,
                view: updateViewFilter(state.all, makeFilterFn(action.filter))
            }
        case SET_HIGHLIGHT:
            return {
                ...state,
                highlight: action.highlight
            }
        case SET_SORT:
            return {
                ...state,
                sort: action.sort
            }
        case SELECT_FLOW:
            return {
                ...state,
                selected: [action.flowId]
            }
        default:
            return state
    }
}


export function setFilter(filter) {
    return {
        type: SET_FILTER,
        filter
    }
}
export function setHighlight(highlight) {
    return {
        type: SET_HIGHLIGHT,
        highlight
    }
}
export  function setSort(sort){
    return {
        type: SET_SORT,
        sort
    }
}
export function selectFlow(flowId) {
    return {
        type: SELECT_FLOW,
        flowId
    }
}


export {updateList as updateFlows, fetchList as fetchFlows}