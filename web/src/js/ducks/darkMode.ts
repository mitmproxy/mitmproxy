import { isDarkModeEnabled, setUiMode } from "../utils";

export const TOGGLE_DARK_MODE = 'TOGGLE_DARK_MODE'

interface DarkModeState {
    on: boolean
}

export const defaultState: DarkModeState = {
    on: isDarkModeEnabled(),
};

export default function reducer(state = defaultState, action): DarkModeState {
    switch (action.type) {
        case TOGGLE_DARK_MODE:
            setUiMode(!state.on)
            return {
                ...state,
                on: !state.on
            }

        default:
            return state
    }
}

export function toggleDarkMode() {
    return {type: TOGGLE_DARK_MODE}
}
