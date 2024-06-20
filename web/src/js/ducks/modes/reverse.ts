import { ModeState, updateMode } from "../modes";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { addListenAddr } from "./utils";

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
                const modes = action.data.mode.value;
                const isActive = modes.some((mode) => mode.includes("reverse"));
                let currentProtocol = "";
                modes.forEach((mode) => {
                    if (mode.startsWith("reverse:")) {
                        currentProtocol = mode.substring("reverse:".length);
                    }
                });
                return {
                    ...state,
                    active: isActive,
                    protocol: action.protocolName !== "" ? action.protocolName : state.protocol,
                    error: undefined,
                };
            }
            return state;
        default:
            return state;
    }
};

export default reverseReducer;
