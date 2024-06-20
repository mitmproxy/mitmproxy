import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { ModeState, updateMode } from "../modes";
import { addListenAddr, getModesOfType } from "./utils";

export const TOGGLE_WIREGUARD = "TOGGLE_WIREGUARD";

interface WireguardState extends ModeState {
    path?: string;
}

export const initialState: WireguardState = {
    active: false,
    name: "wireguard",
    path: "",
};

export const getMode = (modes) => {
    const wireguardMode = modes.wireguard;
    return addListenAddr(wireguardMode);
};

export const toggleWireguard = () => {
    return async (dispatch) => {
        dispatch({ type: TOGGLE_WIREGUARD });

        const result = await dispatch(updateMode());

        if (!result.success) {
            //TODO: handle error
            console.error("error", result.error);
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
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const currentModeConfig = getModesOfType(
                    "wireguard",
                    action.data.mode.value
                )[0];
                const isActive = currentModeConfig !== undefined;
                return {
                    ...state,
                    active: isActive,
                    listen_host:
                        currentModeConfig?.listen_host || state.listen_host,
                    listen_port:
                        currentModeConfig?.listen_port || state.listen_port,
                };
            }
            return state;
        default:
            return state;
    }
};

export default wireguardReducer;
