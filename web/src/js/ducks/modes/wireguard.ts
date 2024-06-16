import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { ModeState, updateMode } from "../modes";

export const TOGGLE_WIREGUARD = "TOGGLE_WIREGUARD";
export const ERROR_WIREGUARD = "ERROR_WIREGUARD";

interface WireguardState extends ModeState {
    path?: string;
}

export const initialState: WireguardState = {
    active: false,
    path: "",
};

export const getMode = (modes) => {
    const wireguardMode = modes.wireguard;
    let mode = "wireguard";
    if (wireguardMode.active) {
        if (wireguardMode.listen_host) {
            mode += `@${wireguardMode.listen_host}`;
        }
        if (wireguardMode.listen_port) {
            mode += `:${wireguardMode.listen_port}`;
        }
        return mode;
    }
    return "";
};

export const toggleWireguard = () => {
    return async (dispatch) => {
        dispatch({ type: TOGGLE_WIREGUARD });

        const result = await dispatch(updateMode());

        if (!result.success) {
            console.error("error", result.error);
            dispatch({ type: ERROR_WIREGUARD, error: result.error });
        }
    };
};

const wireguardReducer = (state = initialState, action): WireguardState => {
    switch (action.type) {
        case TOGGLE_WIREGUARD:
            return {
                ...state,
                active: !state.active,
            };
        case ERROR_WIREGUARD:
            return {
                ...state,
                error: action.error,
            };
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const isActive = action.data.mode.value.includes("wireguard");
                return {
                    ...state,
                    active: isActive,
                };
            }
            return state;
        default:
            return state;
    }
};

export default wireguardReducer;
