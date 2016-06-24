import { fetchApi } from '../utils'
import * as msgQueueActions from './msgQueue'

export const MSG_TYPE = 'UPDATE_SETTINGS'
export const DATA_URL = '/settings'

export const RECEIVE        = 'RECEIVE'
export const UPDATE         = 'UPDATE'
export const REQUEST_UPDATE = 'REQUEST_UPDATE'
export const UNKNOWN_CMD    = 'SETTINGS_UNKNOWN_CMD'

const defaultState = {
    settings: {},
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case RECEIVE:
            return {
                ...state,
                settings: action.settings,
            }

        case UPDATE:
            return {
                ...state,
                settings: { ...state.settings, ...action.settings },
            }

        default:
            return state
    }
}

/**
 * @public msgQueue
 */
export function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_UPDATE:
            return updateSettings(msg.data)

        default:
            console.error('unknown settings update', msg)
            return { type: UNKNOWN_CMD, msg }
    }
}

/**
 * @public
 */
export function update(settings) {
    fetchApi.put('/settings', settings)
    return { type: REQUEST_UPDATE }
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
export function receiveData(settings) {
    return { type: RECEIVE, settings }
}

/**
 * @private
 */
export function updateSettings(settings) {
    return { type: UPDATE, settings }
}
