import { ModeState, updateMode } from "../modes";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { addListenAddr } from "./utils";

export const TOGGLE_REVERSE = "TOGGLE_REVERSE";
export const SET_PROTOCOLS = "SET_PROTOCOLS";

interface ProtocolState {
    name: string;
    isSelected: boolean;
}

export interface ReverseState extends ModeState {
    protocols: ProtocolState[];
}

export const initialState: ReverseState = {
    active: false,
    name: "reverse",
    protocols: [
        { name: "http", isSelected: false },
        { name: "https", isSelected: false },
        { name: "dns", isSelected: false },
        { name: "http3", isSelected: false },
        { name: "quic", isSelected: false },
        { name: "tcp", isSelected: false },
        { name: "tls", isSelected: false },
        { name: "udp", isSelected: false },
        { name: "dtls", isSelected: false },
    ],
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
        dispatch({ type: SET_PROTOCOLS, protocolName: protocolName });

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
        case SET_PROTOCOLS:
            const updatedProtocols = state.protocols.map((protocol) =>
                protocol.name === action.protocolName
                    ? { ...protocol, isSelected: true }
                    : { ...protocol, isSelected: false }
            );
            return {
                ...state,
                protocols: updatedProtocols,
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
                const updatedProtocols = state.protocols.map((protocol) =>
                    currentProtocol === protocol.name
                        ? { ...protocol, isSelected: true }
                        : { ...protocol, isSelected: false }
                );
                return {
                    ...state,
                    active: isActive,
                    protocols: updatedProtocols,
                    error: undefined,
                };
            }
            return state;
        default:
            return state;
    }
};

export default reverseReducer;
