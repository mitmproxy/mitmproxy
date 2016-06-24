import { fetchApi } from '../utils'
import * as websocketActions from './websocket'
import * as eventLogActions from './eventLog'
import * as flowsActions from './flows'
import * as settingsActions from './settings'

export const INIT = 'MSG_QUEUE_INIT'
export const ENQUEUE = 'MSG_QUEUE_ENQUEUE'
export const CLEAR = 'MSG_QUEUE_CLEAR'
export const FETCH_ERROR = 'MSG_QUEUE_FETCH_ERROR'

const handlers = {
    [eventLogActions.MSG_TYPE] : eventLogActions,
    [flowsActions.MSG_TYPE]    : flowsActions,
    [settingsActions.MSG_TYPE] : settingsActions,
}

const defaultState = {}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case INIT:
            return {
                ...state,
                [action.queue]: [],
            }

        case ENQUEUE:
            return {
                ...state,
                [action.queue]: [...state[action.queue], action.msg],
            }

        case CLEAR:
            return {
                ...state,
                [action.queue]: null,
            }

        default:
            return state
    }
}

/**
 * @public websocket
 */
export function handleWsMsg(msg) {
    return (dispatch, getState) => {
        const handler = handlers[msg.type]
        if (msg.cmd === websocketActions.CMD_RESET) {
            return dispatch(fetchData(handler.MSG_TYPE))
        }
        if (getState().msgQueue[handler.MSG_TYPE]) {
            return dispatch({ type: ENQUEUE, queue: handler.MSG_TYPE, msg })
        }
        return dispatch(handler.handleWsMsg(msg))
    }
}

/**
 * @public
 */
export function fetchData(type) {
    return dispatch => {
        const handler = handlers[type]

        dispatch(init(handler.MSG_TYPE))

        fetchApi(handler.DATA_URL)
            .then(res => res.json())
            .then(json => dispatch(receive(type, json)))
            .catch(error => dispatch(fetchError(type, error)))
    }
}

/**
 * @private
 */
export function receive(type, res) {
    return (dispatch, getState) => {
        const handler = handlers[type]
        const queue = getState().msgQueue[handler.MSG_TYPE] || []

        dispatch(clear(handler.MSG_TYPE))
        dispatch(handler.receiveData(res.data))
        for (const msg of queue) {
            dispatch(handler.handleWsMsg(msg))
        }
    }
}

/**
 * @private
 */
export function init(queue) {
    return { type: INIT, queue }
}

/**
 * @private
 */
export function clear(queue) {
    return { type: CLEAR, queue }
}

/**
 * @private
 */
export function fetchError(type, error) {
    return { type: FETCH_ERROR, type, error }
}
