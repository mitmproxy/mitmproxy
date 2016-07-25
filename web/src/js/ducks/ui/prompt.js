export const SET_PROMPT = 'SET_PROMPT'

const defaultState = {
    options: null,
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case SET_PROMPT:
            return {
                ...state,
                options: action.options,
            }

        default:
            return state
    }
}

export function setPrompt(options) {
    return { type: SET_PROMPT, options }
}
