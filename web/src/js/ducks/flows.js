import { fetchApi } from '../utils'
import reduceList, * as listActions from './utils/list'
import { selectRelative } from './flowView'

import * as msgQueueActions from './msgQueue'
import * as websocketActions from './websocket'

export const MSG_TYPE = 'UPDATE_FLOWS'
export const DATA_URL = '/flows'

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
                ...reduceList(state, listActions.receive(action.list)),
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

/**
 * @public
 */
export function accept(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/accept`, { method: 'POST' })
}

/**
 * @public
 */
export function acceptAll() {
    return dispatch => fetchApi('/flows/accept', { method: 'POST' })
}

/**
 * @public
 */
export function remove(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}`, { method: 'DELETE' })
}

/**
 * @public
 */
export function duplicate(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/duplicate`, { method: 'POST' })
}

/**
 * @public
 */
export function replay(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/replay`, { method: 'POST' })
}

/**
 * @public
 */
export function revert(flow) {
    return dispatch => fetchApi(`/flows/${flow.id}/revert`, { method: 'POST' })
}

/**
 * @public
 */
export function update(flow, data) {
    return dispatch => fetchApi.put(`/flows/${flow.id}`, data)
}

export function uploadContent(flow, file, type) {
    const body = new FormData()
    file = new Blob([file], {type: 'plain/text'})
    body.append('file', file)
    return dispatch => fetchApi(`/flows/${flow.id}/${type}/content`, {method: 'post',  body} )
}


/**
 * @public
 */
export function clear() {
    return dispatch => fetchApi('/clear', { method: 'POST' })
}

/**
 * @public
 */
export function download() {
    window.location = '/flows/dump'
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
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


/**
 * This action creater takes all WebSocket events
 *
 * @public websocket
 */
export function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_ADD:
            return addFlow(msg.data)

        case websocketActions.CMD_UPDATE:
            return updateFlow(msg.data)

        case websocketActions.CMD_REMOVE:
            return removeFlow(msg.data.id)

        case websocketActions.CMD_RESET:
            return fetchFlows()

        default:
            return { type: UNKNOWN_CMD, msg }
    }
}

/**
 * @public websocket
 */
export function fetchFlows() {
    return msgQueueActions.fetchData(MSG_TYPE)
}

/**
 * @public msgQueue
 */
export function receiveData(list) {
    return { type: RECEIVE, list }
}

/**
 * @private
 */
export function addFlow(item) {
    return { type: ADD, item }
}

/**
 * @private
 */
export function updateFlow(item) {
    return { type: UPDATE, item }
}

/**
 * @private
 */
export function removeFlow(id) {
    return (dispatch, getState) => {
        let currentIndex = getState().flowView.indexOf[getState().flows.selected[0]]
        let maxIndex = getState().flowView.data.length - 1
        let deleteLastEntry = maxIndex == 0
        if (deleteLastEntry)
            dispatch(select())
        else
            dispatch(selectRelative(currentIndex == maxIndex ? -1 : 1) )
        dispatch({ type: REMOVE, id })
    }
}
