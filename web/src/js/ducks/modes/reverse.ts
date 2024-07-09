import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import {
    ModeState,
    getModesOfType,
    includeModeState,
    parseMode,
    updateMode,
} from "./utils";
import type { ModesState } from "../modes";

export const MODE_REVERSE_TOGGLE = "MODE_REVERSE_TOGGLE";
export const MODE_REVERSE_SET_LISTEN_CONFIG = "MODE_REVERSE_SET_LISTEN_CONFIG";
export const MODE_REVERSE_SET_HOST = "MODE_REVERSE_SET_HOST";
export const MODE_REVERSE_SET_PROTOCOL = "MODE_REVERSE_SET_PROTOCOL";
export const MODE_REVERSE_ERROR = "MODE_REVERSE_ERROR";

export interface ReverseState extends ModeState {
    protocol?: string;
    host?: string;
}

export const initialState: ReverseState = {
    active: false,
    protocol: "",
    host: "",
};

export const getMode = (modes: ModesState): string[] => {
    const mode = `reverse:${modes.reverse.protocol}://${modes.reverse.host}`;
    return includeModeState(mode, modes.reverse);
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

export const setListenConfig =
    (port: number, host: string) => async (dispatch) => {
        dispatch({ type: MODE_REVERSE_SET_LISTEN_CONFIG, port, host });

        try {
            await dispatch(updateMode());
        } catch (e) {
            dispatch({ type: MODE_REVERSE_ERROR, error: e.message });
        }
    };

export const setHost = (host: string) => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_SET_HOST, host });
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
        case MODE_REVERSE_SET_LISTEN_CONFIG:
            return {
                ...state,
                listen_port: action.port as number,
                listen_host: action.host,
                error: undefined,
            };
        case MODE_REVERSE_SET_HOST:
            return {
                ...state,
                host: action.host,
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
            if (action.data && action.data.servers) {
                const currentModeConfig = getModesOfType(
                    "reverse",
                    action.data.servers,
                )[0];
                const isActive = currentModeConfig !== undefined;
                let protocol,
                    host = "";
                if (isActive) {
                    [protocol, host] = currentModeConfig.data.split("://");
                }
                return {
                    ...state,
                    active: isActive,
                    protocol: isActive ? protocol : state.protocol,
                    host: isActive ? host : state.host,
                    listen_host: isActive
                        ? currentModeConfig.listen_host
                        : state.listen_host,
                    listen_port: isActive
                        ? (currentModeConfig.listen_port as number)
                        : state.listen_port,
                    error: isActive ? undefined : state.error,
                };
            }
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
