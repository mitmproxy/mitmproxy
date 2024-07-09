import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { ModeState, includeModeState, updateMode } from "./utils";
import type { ModesState } from "../modes";

export const MODE_REVERSE_TOGGLE = "MODE_REVERSE_TOGGLE";
export const MODE_REVERSE_SET_PORT = "MODE_REVERSE_SET_PORT";
export const MODE_REVERSE_SET_PROTOCOL = "MODE_REVERSE_SET_PROTOCOL";
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

export const setProtocol = (protocol: string) => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_SET_PROTOCOL, protocol: protocol });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_REVERSE_ERROR, error: e.message });
    }
};

export const setPort = (port: number) => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_SET_PORT, port });

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
        case MODE_REVERSE_SET_PORT:
            return {
                ...state,
                listen_port: action.port as number,
                error: undefined,
            };
        case MODE_REVERSE_SET_PROTOCOL:
            return {
                ...state,
                protocol: action.protocol,
                error: undefined,
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
