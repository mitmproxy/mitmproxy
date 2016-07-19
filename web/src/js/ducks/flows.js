import { fetchApi } from '../utils'
import reduceList, * as listActions from './utils/list'
import reduceViews, * as viewsActions from './views'
import * as msgQueueActions from './msgQueue'
import * as websocketActions from './websocket'

export const MSG_TYPE = 'UPDATE_FLOWS'
export const DATA_URL = '/flows'

export const ADD            = 'FLOWS_ADD'
export const UPDATE         = 'FLOWS_UPDATE'
export const REMOVE         = 'FLOWS_REMOVE'
export const RECEIVE        = 'FLOWS_RECEIVE'
export const REQUEST_ACTION = 'FLOWS_REQUEST_ACTION'
export const UNKNOWN_CMD    = 'FLOWS_UNKNOWN_CMD'
export const FETCH_ERROR    = 'FLOWS_FETCH_ERROR'
export const SET_MODIFIED_FLOW_CONTENT = "FLOWS_SET_MODIFIED_FLOW"

const defaultState = {
    list: undefined,
    views: undefined,
    modifiedFlow: {headers: "", content: ""}
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case ADD:
            return {
                ...state,
                list: reduceList(state.list, listActions.add(action.item)),
                views: reduceViews(state.views, viewsActions.add(action.item)),
            }

        case UPDATE:
            return {
                ...state,
                list: reduceList(state.list, listActions.update(action.id, action.item)),
                views: reduceViews(state.views, viewsActions.update(action.id, action.item)),
            }

        case REMOVE:
            return {
                ...state,
                list: reduceList(state.list, listActions.remove(action.id)),
                views: reduceViews(state.views, viewsActions.remove(action.id)),
            }

        case RECEIVE:
            const list = reduceList(state.list, listActions.receive(action.list))
            return {
                ...state,
                list,
                views: reduceViews(state.views, viewsActions.receive(list)),
            }
        case SET_MODIFIED_FLOW_CONTENT:
            return{
                ...state,
                   modifiedFlow: {...state.modifiedFlow, content: action.content}
            }


        default:
            return {
                ...state,
                list: reduceList(state.list, action),
                views: reduceViews(state.views, action),
            }
    }
}

/**
 * @public
 */
export function setModifiedFlowContent(content) {
    return {
        type: SET_MODIFIED_FLOW_CONTENT,
        content
    }
}


/**
 * @public
 */
export function accept(flow) {
    fetchApi(`/flows/${flow.id}/accept`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function acceptAll() {
    fetchApi('/flows/accept', { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function remove(flow) {
    fetchApi(`/flows/${flow.id}`, { method: 'DELETE' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function duplicate(flow) {
    fetchApi(`/flows/${flow.id}/duplicate`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function replay(flow) {
    fetchApi(`/flows/${flow.id}/replay`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function revert(flow) {
    fetchApi(`/flows/${flow.id}/revert`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function update(flow, data) {
    fetchApi.put(`/flows/${flow.id}`, data)
    return { type: REQUEST_ACTION }
}

export function updateContent(flow, file, type) {
    const body = new FormData()
    if (typeof file !== File)
        file = new Blob([file], {type: 'plain/text'})
    body.append('file', file)
    fetchApi(`/flows/${flow.id}/${type}/content`, {method: 'post',  body} )
    return { type: REQUEST_ACTION }
}


/**
 * @public
 */
export function clear() {
    fetchApi('/clear', { method: 'POST' })
    return { type: REQUEST_ACTION }
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
    fetchApi('/flows/dump', { method: 'post', body })
    return { type: REQUEST_ACTION }
}

/**
 * This action creater takes all WebSocket events
 *
 * @public websocket
 */
export function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_ADD:
            return addItem(msg.data)

        case websocketActions.CMD_UPDATE:
            return updateItem(msg.data.id, msg.data)

        case websocketActions.CMD_REMOVE:
            return removeItem(msg.data.id)

        case websocketActions.CMD_RESET:
            return fetchData()

        default:
            return { type: UNKNOWN_CMD, msg }
    }
}

/**
 * @public websocket
 */
export function fetchData() {
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
export function addItem(item) {
    return { type: ADD, item }
}

/**
 * @private
 */
export function updateItem(id, item) {
    return { type: UPDATE, id, item }
}

/**
 * @private
 */
export function removeItem(id) {
    return { type: REMOVE, id }
}
