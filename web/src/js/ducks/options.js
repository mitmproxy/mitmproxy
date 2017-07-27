import { fetchApi } from "../utils"
import * as optionsEditorActions from "./ui/optionsEditor"
import _ from "lodash"

export const RECEIVE = 'OPTIONS_RECEIVE'
export const UPDATE = 'OPTIONS_UPDATE'
export const REQUEST_UPDATE = 'REQUEST_UPDATE'

const defaultState = {}

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

export function pureSendUpdate (option, value, dispatch) {
    fetchApi.put('/options', { [option]: value }).then(response => {
        if (response.status === 200) {
            dispatch(optionsEditorActions.updateSuccess(option))
        } else {
            response.text().then(error => {
                dispatch(optionsEditorActions.updateError(option, error))
            })
        }
    })
}
let sendUpdate = _.throttle(pureSendUpdate, 700, { leading: true, trailing: true })

export function update(option, value) {
    return dispatch => {
        dispatch(optionsEditorActions.startUpdate(option, value))
        sendUpdate(option, value, dispatch);
    }
}

export function save() {
    return dispatch => fetchApi('/options/save', { method: 'POST' })
}
