import reduceList, * as listActions from './utils/list'
import reduceViews, * as viewsActions from './views'

export const WS_MSG_TYPE = 'UPDATE_FLOWS'

export const ADD = 'FLOWS_ADD'
export const UPDATE = 'FLOWS_UPDATE'
export const REMOVE = 'FLOWS_REMOVE'
export const REQUEST = 'FLOWS_REQUEST'
export const RECEIVE = 'FLOWS_RECEIVE'
export const WS_MSG = 'FLOWS_WS_MSG'
export const REQUEST_ACTION = 'FLOWS_REQUEST_ACTION'
export const FETCH_ERROR = 'FLOWS_FETCH_ERROR'

const defaultState = {
    list: null,
    views: null,
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
                list: reduceList(state.list, listActions.update(action.item.id, action.item)),
                views: reduceViews(state.views, viewsActions.update(action.item.id, action.item)),
            }

        case REMOVE:
            return {
                ...state,
                list: reduceList(state.list, listActions.remove(action.item.id)),
                views: reduceViews(state.views, viewsActions.remove(action.item.id)),
            }

        case REQUEST:
            return {
                ...state,
                list: reduceList(state.list, listActions.request()),
            }

        case RECEIVE:
            const list = reduceList(state.list, listActions.receive(action.list))
            return {
                ...state,
                list,
                views: reduceViews(state.views, viewsActions.receive(list)),
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
export function accept(flow) {
    fetch(`/flows/${flow.id}/accept`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function acceptAll() {
    fetch('/flows/accept', { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function remove(flow) {
    fetch(`/flows/${flow.id}`, { method: 'DELETE' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function duplicate(flow) {
    fetch(`/flows/${flow.id}/duplicate`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function replay(flow) {
    fetch(`/flows/${flow.id}/replay`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function revert(flow) {
    fetch(`/flows/${flow.id}/revert`, { method: 'POST' })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function update(flow, body) {
    fetch(`/flows/${flow.id}`, { method: 'PUT', body })
    return { type: REQUEST_ACTION }
}

/**
 * @public
 */
export function clear() {
    fetch('/clear', { method: 'POST' })
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
    fetch('/flows/dump',  { method: 'post', body })
    return { type: REQUEST_ACTION }
}

/**
 * This action creater takes all WebSocket events
 *
 * @public websocket
 */
export function handleWsMsg(msg) {
    if (msg.cmd === WS_CMD_RESET) {
        return fetchData()
    }
    return { type: WS_MSG, msg }
}

/**
 * @public websocket
 */
export function fetchData() {
    return dispatch => {
        dispatch(request())

        return fetch('/flows')
            .then(res => res.json())
            .then(json => dispatch(receive(json.data)))
            .catch(error => dispatch(fetchError(error)))
    }
}

/**
 * @private
 */
export function request() {
    return { type: REQUEST }
}

/**
 * @private
 */
export function receive(list) {
    return { type: RECEIVE, list }
}

/**
 * @private
 */
export function fetchError(error) {
    return { type: FETCH_ERROR, error }
}
