import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import {
    getModesOfType,
    isActiveMode,
    includeListenAddress,
    ModeState,
    updateMode,
} from "./utils";
import type { ModesState } from "../modes";

export const MODE_WIREGUARD_TOGGLE = "MODE_WIREGUARD_TOGGLE";
export const MODE_WIREGUARD_ERROR = "MODE_WIREGUARD_ERROR";
export const MODE_WIREGUARD_SET_PORT = "MODE_WIREGUARD_SET_PORT";
export const MODE_WIREGUARD_SET_HOST = "MODE_WIREGUARD_SET_HOST";
export const MODE_WIREGUARD_SET_FILE_PATH = "MODE_WIREGUARD_SET_FILE_PATH";

interface WireguardState extends ModeState {
    file_path?: string;
}

export const initialState: WireguardState = {
    active: false,
    file_path: "",
    listen_port: 51820,
};

export const getSpecs = ({ wireguard }: ModesState): string[] => {
    if (!isActiveMode(wireguard)) {
        return [];
    }
    return [includeListenAddress("wireguard", wireguard)];
};

export const toggleWireguard = () => async (dispatch) => {
    dispatch({ type: MODE_WIREGUARD_TOGGLE });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_WIREGUARD_ERROR, error: e.message });
    }
};

export const setPort = (port: number) => async (dispatch) => {
    dispatch({ type: MODE_WIREGUARD_SET_PORT, port });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_WIREGUARD_ERROR, error: e.message });
    }
};

export const setHost = (host: string) => async (dispatch) => {
    dispatch({ type: MODE_WIREGUARD_SET_HOST, host });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_WIREGUARD_ERROR, error: e.message });
    }
};

export const setFilePath = (path: string) => async (dispatch) => {
    dispatch({ type: MODE_WIREGUARD_SET_FILE_PATH, path });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_WIREGUARD_ERROR, error: e.message });
    }
};

const wireguardReducer = (state = initialState, action): WireguardState => {
    switch (action.type) {
        case MODE_WIREGUARD_TOGGLE:
            return {
                ...state,
                active: !state.active,
            };
        case MODE_WIREGUARD_SET_PORT:
            return {
                ...state,
                listen_port: action.port as number,
                error: undefined,
            };
        case MODE_WIREGUARD_SET_HOST:
            return {
                ...state,
                listen_host: action.host,
                error: undefined,
            };
        case MODE_WIREGUARD_SET_FILE_PATH:
            return {
                ...state,
                file_path: action.path,
                error: undefined,
            };
        case UPDATE_STATE.type:
        case RECEIVE_STATE.type:
            if (action.data && action.data.servers) {
                const currentModeConfig = getModesOfType(
                    "wireguard",
                    action.data.servers,
                )[0];
                const isActive = currentModeConfig !== undefined;
                return {
                    ...state,
                    active: isActive,
                    listen_host: isActive
                        ? currentModeConfig.listen_host
                        : state.listen_host,
                    listen_port: isActive
                        ? (currentModeConfig.listen_port as number)
                        : state.listen_port,
                    file_path: isActive
                        ? currentModeConfig.data
                        : state.file_path,
                    error: isActive ? undefined : state.error,
                };
            }
            return state;
        case MODE_WIREGUARD_ERROR:
            return {
                ...state,
                error: action.error,
            };
        default:
            return state;
    }
};

export default wireguardReducer;
