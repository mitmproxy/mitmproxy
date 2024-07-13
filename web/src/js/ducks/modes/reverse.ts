import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import {
    ModeState,
    getModesOfType,
    includeModeState,
    updateMode,
} from "./utils";
import type { ModesState } from "../modes";
import { ReverseProxyProtocols } from "../../backends/consts";

export const MODE_REVERSE_TOGGLE = "MODE_REVERSE_TOGGLE";
export const MODE_REVERSE_SET_LISTEN_CONFIG = "MODE_REVERSE_SET_LISTEN_CONFIG";
export const MODE_REVERSE_SET_DESTINATION = "MODE_REVERSE_SET_DESTINATION";
export const MODE_REVERSE_SET_PROTOCOL = "MODE_REVERSE_SET_PROTOCOL";
export const MODE_REVERSE_ERROR = "MODE_REVERSE_ERROR";

export interface ReverseState extends ModeState {
    protocol?: ReverseProxyProtocols;
    destination?: string;
}

export const initialState: ReverseState = {
    active: false,
    protocol: ReverseProxyProtocols.HTTPS,
    destination: "",
};

export const getMode = (modes: ModesState): string[] => {
    const mode = `reverse:${modes.reverse.protocol}://${modes.reverse.destination}`;
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

export const setProtocol =
    (protocol: ReverseProxyProtocols) => async (dispatch) => {
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

export const setDestination = (destination: string) => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_SET_DESTINATION, destination });
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
        case MODE_REVERSE_SET_DESTINATION:
            return {
                ...state,
                destination: action.destination,
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
                    destination = "";
                if (isActive) {
                    [protocol, destination] =
                        currentModeConfig.data.split("://");
                }
                return {
                    ...state,
                    active: isActive,
                    protocol: isActive ? protocol : state.protocol,
                    destination: isActive ? destination : state.destination,
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
