import { fetchApi } from '../utils'
import reduceList, * as listActions from './utils/list'
import { selectRelative } from './flowView'

export const ADD = 'FLOWS_ADD'
export const UPDATE = 'FLOWS_UPDATE'
export const REMOVE = 'FLOWS_REMOVE'
export const RECEIVE = 'FLOWS_RECEIVE'
export const REQUEST_ACTION = 'FLOWS_REQUEST_ACTION'
export const UNKNOWN_CMD = 'FLOWS_UNKNOWN_CMD'
export const FETCH_ERROR = 'FLOWS_FETCH_ERROR'
export const SELECT = 'FLOWS_SELECT'


const defaultState = {
    selected: [],
    ...reduceList(undefined, {}),
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case ADD:
            return {
                ...state,
                ...reduceList(state, listActions.add(action.item)),
            }

        case UPDATE:
            return {
                ...state,
                ...reduceList(state, listActions.update(action.item)),
            }

        case REMOVE:
            return {
                ...state,
                ...reduceList(state, listActions.remove(action.id)),
            }

        case RECEIVE:
            return {
                ...state,
                ...reduceList(state, listActions.receive(action.flows)),
            }

        case SELECT:
            return {
                ...state,
                selected: action.flowIds
            }

        default:
            return {
                ...state,
                ...reduceList(state, action),
            }
    }
}

export function accept(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/accept`, { method: 'POST' })
}

export function acceptAll() {
    return dispatch => fetchApi('/flows/accept', { method: 'POST' })
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
    file = new Blob([file], {type: 'plain/text'})
    body.append('file', file)
    return dispatch => fetchApi(`/flows/${flow.id}/${type}/content`, {method: 'post',  body} )
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
    return dispatch => fetchApi('/flows/dump', { method: 'post', body })
}


export function select(id) {
    return {
        type: SELECT,
        flowIds: id ? [id] : []
    }
}
