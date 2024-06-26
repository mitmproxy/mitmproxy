import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import {
    ModeState,
    includeModeState,
    updateMode,
    getModesOfType,
} from "./utils";

export const MODE_WIREGUARD_TOGGLE = "MODE_WIREGUARD_TOGGLE";

interface WireguardState extends ModeState {
    path?: string;
}

export const initialState: WireguardState = {
    active: false,
    path: "",
};

export const getMode = (modes) => {
    const wireguardMode = modes.wireguard;
    return includeModeState("wireguard", wireguardMode);
};

export const toggleWireguard = () => {
    return async (dispatch) => {
        dispatch({ type: MODE_WIREGUARD_TOGGLE });

        const result = await dispatch(updateMode());

        if (!result.success) {
            //TODO: handle error
        }
    };
};

const wireguardReducer = (state = initialState, action): WireguardState => {
    switch (action.type) {
        case MODE_WIREGUARD_TOGGLE:
            return {
                ...state,
                active: !state.active,
            };
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const currentModeConfig = getModesOfType(
                    "wireguard",
                    action.data.mode.value,
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
                };
            }
            return state;
        default:
            return state;
    }
};

export default wireguardReducer;
