import { fetchApi } from "../utils"
import reduceStore from "./utils/store"
import * as storeActions from "./utils/store"
import Filt from "../filt/filt"
import { RequestUtils } from "../flow/utils"

export const ADD            = 'FLOWS_ADD'
export const UPDATE         = 'FLOWS_UPDATE'
export const REMOVE         = 'FLOWS_REMOVE'
export const RECEIVE        = 'FLOWS_RECEIVE'
export const SELECT         = 'FLOWS_SELECT'
export const SET_FILTER     = 'FLOWS_SET_FILTER'
export const SET_SORT       = 'FLOWS_SET_SORT'
export const SET_HIGHLIGHT  = 'FLOWS_SET_HIGHLIGHT'
export const REQUEST_ACTION = 'FLOWS_REQUEST_ACTION'


const defaultState = {
    highlight: null,
    filter: null,
    sort: { column: null, desc: false },
    selected: [],
    ...reduceStore(undefined, {})
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case ADD:
        case UPDATE:
        case REMOVE:
        case RECEIVE:
            let storeAction = storeActions[action.cmd](
                action.data,
                makeFilter(state.filter),
                makeSort(state.sort)
            )

            let selected = state.selected
            if(action.type === REMOVE && state.selected.includes(action.data)) {
                if(state.selected.length > 1){
                    selected = selected.filter(x => x !== action.data)
                } else {
                    selected = []
                    if (action.data in state.viewIndex && state.view.length > 1) {
                        let currentIndex = state.viewIndex[action.data],
                            nextSelection
                        if(currentIndex === state.view.length -1){ // last row
                            nextSelection = state.view[currentIndex - 1]
                        } else {
                            nextSelection = state.view[currentIndex + 1]
                        }
                        selected.push(nextSelection.id)
                    }
                }
            }

            return {
                ...state,
                selected,
                ...reduceStore(state, storeAction)
            }

        case SET_FILTER:
            return {
                ...state,
                filter: action.filter,
                ...reduceStore(state, storeActions.setFilter(makeFilter(action.filter), makeSort(state.sort)))
            }

        case SET_HIGHLIGHT:
            return {
                ...state,
                highlight: action.highlight
            }

        case SET_SORT:
            return {
                ...state,
                sort: action.sort,
                ...reduceStore(state, storeActions.setSort(makeSort(action.sort)))
            }

        case SELECT:
            return {
                ...state,
                selected: action.flowIds
            }

        default:
            return state
    }
}


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

export function makeFilter(filter) {
    if (!filter) {
        return
    }
    return Filt.parse(filter)
}

export function makeSort({ column, desc }) {
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

export function setFilter(filter) {
    return { type: SET_FILTER, filter }
}

export function setHighlight(highlight) {
    return { type: SET_HIGHLIGHT, highlight }
}

export function setSort(column, desc) {
    return { type: SET_SORT, sort: { column, desc } }
}

export function selectRelative(flows, shift) {
    let currentSelectionIndex = flows.viewIndex[flows.selected[0]]
    let minIndex = 0
    let maxIndex = flows.view.length - 1
    let newIndex
    if (currentSelectionIndex === undefined) {
        newIndex = (shift < 0) ? minIndex : maxIndex
    } else {
        newIndex = currentSelectionIndex + shift
        newIndex = window.Math.max(newIndex, minIndex)
        newIndex = window.Math.min(newIndex, maxIndex)
    }
    let flow = flows.view[newIndex]
    return select(flow ? flow.id : undefined)
}


export function resume(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/resume`, { method: 'POST' })
}

export function resumeAll() {
    return dispatch => fetchApi('/flows/resume', { method: 'POST' })
}

export function kill(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/kill`, { method: 'POST' })
}

export function killAll() {
    return dispatch => fetchApi('/flows/kill', { method: 'POST' })
}


export function remove(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}`, { method: 'DELETE' })
}

export function duplicate(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/duplicate`, { method: 'POST' })
}

export function replay(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/replay`, { method: 'POST' })
}

export function revert(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/revert`, { method: 'POST' })
}

export function update(flow, data) {
    return dispatch => fetchApi.put(`/flows/${flow.id}`, data)
}

export function uploadContent(flow, file, type) {
    const body = new FormData()
    file       = new window.Blob([file], { type: 'plain/text' })
    body.append('file', file)
    return dispatch => fetchApi(`/flows/${flow.id}/${type}/content.data`, { method: 'POST', body })
}


export function clear() {
    return dispatch => fetchApi('/clear', { method: 'POST' })
}

export function download() {
    window.location = '/flows/dump'
    return { type: REQUEST_ACTION }
}

export function upload(file) {
    const body = new FormData()
    body.append('file', file)
    return dispatch => fetchApi('/flows/dump', { method: 'POST', body })
}


export function select(id) {
    return {
        type: SELECT,
        flowIds: id ? [id] : []
    }
}
