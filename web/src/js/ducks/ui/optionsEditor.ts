import { HIDE_MODAL } from "./modal"

export const OPTION_UPDATE_START = 'UI_OPTION_UPDATE_START'
export const OPTION_UPDATE_SUCCESS = 'UI_OPTION_UPDATE_SUCCESS'
export const OPTION_UPDATE_ERROR = 'UI_OPTION_UPDATE_ERROR'

const defaultState = {
    /* optionName -> {isUpdating, value (client-side), error} */
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case OPTION_UPDATE_START:
            return {
                ...state,
                [action.option]: {
                    isUpdating: true,
                    value: action.value,
                    error: false,
                }
            }

        case OPTION_UPDATE_SUCCESS:
            return {
                ...state,
                [action.option]: undefined
            }

        case OPTION_UPDATE_ERROR:
            let val = state[action.option].value;
            if (typeof(val) === "boolean") {
                // If a boolean option errs, reset it to its previous state to be less confusing.
                // Example: Start mitmweb, check "add_upstream_certs_to_client_chain".
                val = !val;
            }
            return {
                ...state,
                [action.option]: {
                    value: val,
                    isUpdating: false,
                    error: action.error
                }
            }

        case HIDE_MODAL:
            return {}

        default:
            return state
    }
}

export function startUpdate(option, value) {
    return {
        type: OPTION_UPDATE_START,
        option,
        value,
    }
}
export function updateSuccess(option) {
    return {
        type: OPTION_UPDATE_SUCCESS,
        option,
    }
}

export function updateError(option, error) {
    return {
        type: OPTION_UPDATE_ERROR,
        option,
        error,
    }
}
