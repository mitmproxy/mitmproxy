import { fetchApi } from '../utils'

export const RECEIVE        = 'OPTIONS_RECEIVE'
export const UPDATE         = 'OPTIONS_UPDATE'
export const REQUEST_UPDATE = 'REQUEST_UPDATE'
export const UNKNOWN_CMD    = 'OPTIONS_UNKNOWN_CMD'

const defaultState = {

}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case RECEIVE:
            return action.data

        case UPDATE:
            return {
                ...state,
                ...action.data,
            }

        default:
            return state
    }
}

export function update(options) {
    fetchApi.put('/options', options)
    return { type: REQUEST_UPDATE }
}
