import _ from 'lodash'
import * as websocketActions from '../websocket'

export const SET = 'LIST_SET'
export const CLEAR = 'LIST_CLEAR'
export const UNKNOWN_CMD = 'LIST_UNKNOWN_CMD'
export const REQUEST = 'LIST_REQUEST'
export const RECEIVE = 'LIST_RECEIVE'

const defaultState = {
    data: {},
    pendingActions: null,
}

export default function reduce(state = defaultState, action) {
    if (state.pendingActions && action.type !== RECEIVE) {
        return {
            ...state,
            pendingActions: [...state.pendingActions, action]
        }
    }

    switch (action.type) {

        case SET:
            return {
                ...state,
                data: { ...state.data, [action.id]: null, [action.item.id]: action.item }
            }

        case CLEAR:
            return {
                ...state,
                data: { ...state.data, [action.id]: null }
            }

        case REQUEST:
            return {
                ...state,
                pendingActions: []
            }

        case RECEIVE:
            return state.pendingActions.reduce(reduce, {
                ...state,
                pendingActions: null,
                data: _.fromPairs(action.list.map(item => [item.id, item])),
            })

        default:
            return state
    }
}

/**
 * @public
 */
export function add(item) {
    return { type: SET, id: item.id, item }
}

/**
 * @public
 */
export function update(id, item) {
    return { type: SET, id, item }
}

/**
 * @public
 */
export function remove(id) {
    return { type: CLEAR, id }
}

/**
 * @public
 */
export function request() {
    return { type: REQUEST }
}

/**
 * @public
 */
export function receive(list) {
    return { type: RECEIVE, list }
}

/**
 * @public websocket
 */
export function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_ADD:
            return add(msg.data)

        case websocketActions.CMD_UPDATE:
            return update(msg.data.id, msg.data)

        case websocketActions.CMD_REMOVE:
            return remove(msg.data.id)

        default:
            return { type: UNKNOWN_CMD, msg }
    }
}
