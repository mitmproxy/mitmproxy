import {fetchApi} from '../utils'
import {AnyAction, Reducer} from "redux";

export const RECEIVE = 'SETTINGS_RECEIVE'
export const UPDATE = 'SETTINGS_UPDATE'
export const REQUEST_UPDATE = 'REQUEST_UPDATE'

// We currently have everything optional, alternatively we could also provide defaults.
interface SettingsState {
    version?: string
    mode?: string
    intercept_active?: boolean
    intercept?: string
    showhost?: boolean
    upstream_cert?: boolean
    rawtcp?: boolean
    http2?: boolean
    websocket?: boolean
    anticache?: boolean
    anticomp?: boolean
    stickyauth?: string
    stickycookie?: string
    stream?: string
    contentViews?: string[]
    listen_host?: string
    listen_port?: number
    server?: boolean
}

const defaultState: SettingsState = {
}

const reducer: Reducer<SettingsState> = (state = defaultState, action): SettingsState => {
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
export default reducer

export function update(settings) {
    fetchApi.put('/settings', settings)
    return {type: REQUEST_UPDATE}
}

export function addInterceptFilter(example) {
    return (dispatch, getState) => {
        let intercept = getState().settings.intercept;
        if (intercept && intercept.includes(example)) {
            return
        }
        if (!intercept) {
            intercept = example
        } else {
            intercept = `${intercept} | ${example}`
        }
        dispatch(update({intercept}));
    }
}
