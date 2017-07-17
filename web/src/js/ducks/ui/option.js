export const OPTION_UPDATE_START   = 'UI_OPTION_UPDATE_START'
export const OPTION_UPDATE_SUCCESS = 'UI_OPTION_UPDATE_SUCCESS'
export const OPTION_UPDATE_ERROR   = 'UI_OPTION_UPDATE_ERROR'

const defaultState = {
    /* optionName -> {isUpdating, value (client-side), error} */
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case OPTION_UPDATE_START:
            return {
                ...state,
                [action.option]: {
                    isUpdate: true,
                    value: action.value,
                    error: false,
                }
            }

        case OPTION_UPDATE_SUCCESS:
            let s = {...state}
            delete s[action.option]
            return s

        case OPTION_UPDATE_ERROR:
            return {
                ...state,
                [action.option]: {
                    ...state[action.option],
                    isUpdating: false,
                    error: action.error
                }
            }

        default:
            return state
    }
}
