import { fetchApi } from '../utils'
import  * as optionActions from './ui/option'

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
    return dispatch => {
        let option = Object.keys(options)[0]
        dispatch({ type: optionActions.OPTION_UPDATE_START, option, value: options[option] })
        fetchApi.put('/options', options).then(response => {
            if (response.status === 200) {
                dispatch({ type: optionActions.OPTION_UPDATE_SUCCESS, option})
            } else {
                response.text().then( text => {
                    dispatch({type: optionActions.OPTION_UPDATE_ERROR, error: text, option})
                })
            }
        })
    }
}
