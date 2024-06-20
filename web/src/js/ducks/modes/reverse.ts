import { ModeState, updateMode } from "../modes";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { addListenAddr, getModesOfType } from "./utils";

export const TOGGLE_REVERSE = "TOGGLE_REVERSE";
export const SET_PROTOCOL = "SET_PROTOCOL";


export interface ReverseState extends ModeState {
    protocol: string;
}

export const initialState: ReverseState = {
    active: false,
    name: "reverse",
    protocol: "http" || "https" || "dns" || "http3" || "quic" || "tcp" || "tls" || "udp" || "dtls",
};

export const getMode = (modes) => {
    const reverseMode = modes.reverse;
    return addListenAddr(reverseMode)
};

export const toggleReverse = () => {
    return async (dispatch) => {
        dispatch({ type: TOGGLE_REVERSE });

        const result = await dispatch(updateMode());

        if (!result.success) {
            //TODO: handle error
            console.error("error", result.error);
        }
    };
};

export const addProtocols = (protocolName: string) => {
    return async (dispatch, getState) => {
        dispatch({ type: SET_PROTOCOL, protocolName: protocolName });

        const mode = getState().modes.reverse;

        if (mode.active) {
            const result = await dispatch(updateMode());

            if (!result.success) {
                //TODO: handle error
                console.error("error", result.error);
            }
        }
    };
};

const reverseReducer = (state = initialState, action): ReverseState => {
    switch (action.type) {
        case TOGGLE_REVERSE:
            return {
                ...state,
                active: !state.active,
                error: undefined,
            };
        case SET_PROTOCOL:
            return {
                ...state,
                protocol: action.protocolName,
                error: undefined,
            };
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const currentModeConfig = getModesOfType("reverse", action.data.mode.value)[0] //remove [0] TODO
                const isActive = currentModeConfig !== undefined
                return {
                    ...state,
                    active: isActive,
                    protocol: currentModeConfig?.protocol || state.protocol,
                    listen_host: currentModeConfig?.listen_host || state.listen_host,
                    listen_port: currentModeConfig?.listen_port || state.listen_port,
                    error: undefined,
                };
            }
            return state;
        default:
            return state;
    }
};

export default reverseReducer;
