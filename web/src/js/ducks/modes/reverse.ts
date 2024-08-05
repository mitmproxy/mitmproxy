import {
    ModeState,
    getModesOfType,
    includeListenAddress,
    isActiveMode,
    updateMode,
} from "./utils";
import type { ModesState } from "../modes";
import { ReverseProxyProtocols } from "../../backends/consts";
import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { partition } from "../../utils";
import { shallowEqual } from "react-redux";

export const MODE_REVERSE_TOGGLE = "MODE_REVERSE_TOGGLE";
export const MODE_REVERSE_SET_LISTEN_CONFIG = "MODE_REVERSE_SET_LISTEN_CONFIG";
export const MODE_REVERSE_SET_DESTINATION = "MODE_REVERSE_SET_DESTINATION";
export const MODE_REVERSE_SET_PROTOCOL = "MODE_REVERSE_SET_PROTOCOL";
export const MODE_REVERSE_ERROR = "MODE_REVERSE_ERROR";
export const MODE_REVERSE_ADD_SERVER_CONFIG = "MODE_REVERSE_ADD_SERVER_CONFIG";
export const MODE_REVERSE_DELETE = "MODE_REVERSE_DELETE";

export interface ReverseState extends ModeState {
    protocol: ReverseProxyProtocols;
    destination: string;
}

export const defaultReverseServerConfig: ReverseState = {
    active: false,
    protocol: ReverseProxyProtocols.HTTPS,
    destination: "",
};

type ReverseServersState = ReverseState[];

export const initialState: ReverseServersState = [defaultReverseServerConfig];

const getSpec = (state: ReverseState): string => {
    return includeListenAddress(
        `reverse:${state.protocol}://${state.destination}`,
        state,
    );
};

export const getSpecs = ({ reverse }: ModesState): string[] => {
    return reverse.filter(isActiveMode).map(getSpec);
};

export const addReverseServer = () => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_ADD_SERVER_CONFIG });
};

export const toggleReverse = (modeIndex: number) => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_TOGGLE, index: modeIndex });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({
            type: MODE_REVERSE_ERROR,
            error: e.message,
            index: modeIndex,
        });
    }
};

export const deleteReverse = (modeIndex: number) => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_DELETE, index: modeIndex });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({
            type: MODE_REVERSE_ERROR,
            error: e.message,
            index: modeIndex,
        });
    }
};

export const setProtocol =
    (protocol: ReverseProxyProtocols, modeIndex: number) =>
    async (dispatch) => {
        dispatch({
            type: MODE_REVERSE_SET_PROTOCOL,
            protocol: protocol,
            index: modeIndex,
        });

        try {
            await dispatch(updateMode());
        } catch (e) {
            dispatch({
                type: MODE_REVERSE_ERROR,
                error: e.message,
                index: modeIndex,
            });
        }
    };

export const setListenConfig =
    (port: number, host: string, modeIndex: number) => async (dispatch) => {
        dispatch({
            type: MODE_REVERSE_SET_LISTEN_CONFIG,
            port,
            host,
            index: modeIndex,
        });

        try {
            await dispatch(updateMode());
        } catch (e) {
            dispatch({
                type: MODE_REVERSE_ERROR,
                error: e.message,
                index: modeIndex,
            });
        }
    };

export const setDestination =
    (destination: string, modeIndex: number) => async (dispatch) => {
        dispatch({
            type: MODE_REVERSE_SET_DESTINATION,
            destination,
            index: modeIndex,
        });
        try {
            await dispatch(updateMode());
        } catch (e) {
            dispatch({
                type: MODE_REVERSE_ERROR,
                error: e.message,
                index: modeIndex,
            });
        }
    };

const reverseReducer = (state = initialState, action): ReverseServersState => {
    switch (action.type) {
        case MODE_REVERSE_ADD_SERVER_CONFIG:
            return [...state, defaultReverseServerConfig];
        case MODE_REVERSE_TOGGLE:
            return state.map((server, index) =>
                index === action.index
                    ? {
                          ...server,
                          active: !server.active,
                          error: undefined,
                      }
                    : server,
            );
        case MODE_REVERSE_DELETE:
            return state.filter((_, index) => index !== action.index);
        case MODE_REVERSE_SET_LISTEN_CONFIG:
            return state.map((server, index) =>
                index === action.index
                    ? {
                          ...server,
                          listen_port: action.port,
                          listen_host: action.host,
                          error: undefined,
                      }
                    : server,
            );
        case MODE_REVERSE_SET_DESTINATION:
            return state.map((server, index) =>
                index === action.index
                    ? {
                          ...server,
                          destination: action.destination,
                          error: undefined,
                      }
                    : server,
            );
        case MODE_REVERSE_SET_PROTOCOL:
            return state.map((server, index) =>
                index === action.index
                    ? {
                          ...server,
                          protocol: action.protocol,
                          error: undefined,
                      }
                    : server,
            );
        case UPDATE_STATE:
        case RECEIVE_STATE:
            if (action.data && action.data.servers) {
                // action.data.servers does not include servers that are currently inactive,
                // but we want to keep them in the UI. So we need to merge UI state with what we got from the server.

                const activeServers = Object.fromEntries(
                    getModesOfType("reverse", action.data.servers).map((x) => [
                        x.full_spec,
                        x,
                    ]),
                );

                const nextState: ReverseState[] = [];

                // keep current UI state as is, but correct `active` bit.
                for (const server of state) {
                    const spec = getSpec(server);
                    const active = spec in activeServers;
                    delete activeServers[spec];
                    nextState.push({
                        ...server,
                        active,
                    });
                }

                // add all new specs
                for (const { data, listen_host, listen_port } of Object.values(
                    activeServers,
                )) {
                    let [protocol, destination] = partition(data!, "://") as [
                        ReverseProxyProtocols,
                        string,
                    ];
                    if (!destination) {
                        destination = protocol;
                        protocol = ReverseProxyProtocols.HTTPS;
                    }
                    nextState.push({
                        active: true,
                        protocol,
                        destination,
                        listen_host,
                        listen_port,
                    });
                }

                // remove default config if still present.
                if (
                    nextState.length > 1 &&
                    shallowEqual(nextState[0], defaultReverseServerConfig)
                ) {
                    nextState.shift();
                }

                return nextState;
            }
            return state;

        case MODE_REVERSE_ERROR:
            return state.map((server, index) =>
                index === action.index
                    ? {
                          ...server,
                          error: action.error,
                      }
                    : server,
            );
        default:
            return state;
    }
};

export default reverseReducer;
