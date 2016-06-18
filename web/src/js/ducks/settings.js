import {fetchApi} from "../utils";

export const REQUEST_SETTINGS = "REQUEST_SETTINGS"
export const RECEIVE_SETTINGS = "RECEIVE_SETTINGS"
export const UPDATE_SETTINGS = "UPDATE_SETTINGS"

const defaultState = {
    settings: {},
    isFetching: false,
    actionsDuringFetch: [],
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case REQUEST_SETTINGS:
            return {
                ...state,
                isFetching: true
            }

        case RECEIVE_SETTINGS:
            let s = {
                settings: action.settings,
                isFetching: false,
                actionsDuringFetch: [],
            }
            for (action of state.actionsDuringFetch) {
                s = reducer(s, action)
            }
            return s

        case UPDATE_SETTINGS:
            if (state.isFetching) {
                return {
                    ...state,
                    actionsDuringFetch: [...state.actionsDuringFetch, action]
                }
            }
            return {
                ...state,
                settings: {...state.settings, ...action.settings}
            }

        default:
            return state
    }
}

export function updateSettings(event) {
    /* This action creator takes all WebSocket events */
    if (event.cmd === "update") {
        return {
            type: UPDATE_SETTINGS,
            settings: event.data
        }
    }
    console.error("unknown settings update", event)
}

export function fetchSettings() {
    return dispatch => {
        dispatch({type: REQUEST_SETTINGS})

        return fetchApi("/settings")
            .then(response => response.json())
            .then(json =>
                dispatch({type: RECEIVE_SETTINGS, settings: json.data})
            )
        // TODO: Error handling
    }
}

export function setInterceptPattern(intercept) {
    return dispatch =>
        fetchApi.put("/settings", {intercept})
}
