import { ModeState, updateMode } from "../modes";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";

const TOGGLE_REVERSE = "TOGGLE_REVERSE";
const ERROR_REVERSE = "ERROR_REVERSE";
const SET_PROTOCOLS = "SET_PROTOCOLS";

interface ProtocolState {
    name: string;
    isSelected: boolean;
}

interface ReverseState extends ModeState {
    protocols: ProtocolState[];
}

const initialState: ReverseState = {
    active: false,
    protocols: [
        { name: "http", isSelected: true },
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
    let mode = "reverse";
    if (reverseMode.active) {
        for (const protocol of reverseMode.protocols) {
            if (protocol.isSelected) {
                mode += `:${protocol.name}`;
                if (reverseMode.listen_host) {
                    mode += `@${reverseMode.listen_host}`;
                }
                if (reverseMode.listen_port) {
                    mode += `:${reverseMode.listen_port}`;
                }
                return mode;
            }
        }
    }
    return "";
};

export const toggleReverse = () => {
    return async (dispatch) => {
        dispatch({ type: TOGGLE_REVERSE });

        const result = await dispatch(updateMode());

        if (!result.success) {
            console.error("error", result.error);
            dispatch({ type: ERROR_REVERSE, error: result.error });
        }
    };
};

export const addProtocols = (protocolName: string) => {
    return async (dispatch) => {
        dispatch({ type: SET_PROTOCOLS, protocol: protocolName });

        const result = await dispatch(updateMode());

        if (!result.success) {
            console.error("error", result.error);
            dispatch({ type: ERROR_REVERSE, error: result.error });
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
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const modes = action.data.mode.value;
                const isActive = modes.some((mode) => mode.includes("reverse"));
                let currentProtocols = "";
                modes.forEach((mode) => {
                    if (mode.startsWith("reverse:")) {
                        currentProtocols = mode.substring("reverse:".length);
                    }
                });
                const updatedProtocols = state.protocols.map((protocol) =>
                    currentProtocols.includes(protocol.name)
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
        case SET_PROTOCOLS:
            const updatedProtocols = state.protocols.map((protocol) =>
                protocol.name === action.protocol
                    ? { ...protocol, isSelected: true }
                    : { ...protocol, isSelected: false }
            );
            return {
                ...state,
                protocols: updatedProtocols,
                error: undefined,
            };
        case ERROR_REVERSE:
            return {
                ...state,
                error: action.error,
            };
        default:
            return state;
    }
};

export default reverseReducer;
