import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import {
    ModeState,
    includeModeState,
    updateMode,
    getModesOfType,
} from "./utils";
import type { ModesState } from "../modes";

export const MODE_REVERSE_TOGGLE = "MODE_REVERSE_TOGGLE";
export const MODE_REVERSE_ERROR = "MODE_REVERSE_ERROR";

interface ReverseState extends ModeState {
    protocol?: string;
}

export const initialState: ReverseState = {
    active: false,
    protocol: "",
};

export const getMode = (modes: ModesState): string[] => {
    return includeModeState("reverse", modes.reverse);
};

export const toggleReverse = () => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_TOGGLE });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_REVERSE_ERROR, error: e.message });
    }
};

const reverseReducer = (state = initialState, action): ReverseState => {
    switch (action.type) {
        case MODE_REVERSE_TOGGLE:
            return {
                ...state,
                active: !state.active,
            };
        case UPDATE_STATE:
        case RECEIVE_STATE:
            return state;
        case MODE_REVERSE_ERROR:
            return {
                ...state,
                error: action.error,
            };
        default:
            return state;
    }
};

export default reverseReducer;
