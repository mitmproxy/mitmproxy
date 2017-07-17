import { fetchApi } from '../utils'

export const RECEIVE        = 'SETTINGS_RECEIVE'
export const UPDATE         = 'SETTINGS_UPDATE'
export const REQUEST_UPDATE = 'REQUEST_UPDATE'

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

export function update(settings) {
    fetchApi.put('/settings', settings)
    return { type: REQUEST_UPDATE }
}
