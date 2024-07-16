import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import {
    getModesOfType,
    includeModeState,
    ModeState,
    updateMode,
} from "./utils";
import type { ModesState } from "../modes";

export const MODE_WIREGUARD_TOGGLE = "MODE_WIREGUARD_TOGGLE";
export const MODE_WIREGUARD_ERROR = "MODE_WIREGUARD_ERROR";

interface WireguardState extends ModeState {
    path?: string;
}

export const initialState: WireguardState = {
    active: false,
    path: "",
};

export const getMode = (modes: ModesState): string[] => {
    return includeModeState("wireguard", modes.wireguard);
};

export const toggleWireguard = () => async (dispatch) => {
    dispatch({ type: MODE_WIREGUARD_TOGGLE });

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
        case UPDATE_STATE:
        case RECEIVE_STATE:
            if (action.data && action.data.servers) {
                const currentModeConfig = getModesOfType(
                    "wireguard",
                    action.data.servers,
                )[0];
                const isActive = currentModeConfig !== undefined;
                return {
                    ...state,
                    active: isActive,
                    path: isActive ? currentModeConfig.data : state.path,
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
