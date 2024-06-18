import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { ModeState, updateMode } from "../modes";
import { addListenAddr } from "./utils";

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
