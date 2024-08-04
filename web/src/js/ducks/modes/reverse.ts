import {
    ModeState,
    getModesOfType,
    includeModeState,
    updateMode,
} from "./utils";
import type { ModesState } from "../modes";
import { ReverseProxyProtocols } from "../../backends/consts";
import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";

export const MODE_REVERSE_TOGGLE = "MODE_REVERSE_TOGGLE";
export const MODE_REVERSE_SET_LISTEN_CONFIG = "MODE_REVERSE_SET_LISTEN_CONFIG";
export const MODE_REVERSE_SET_DESTINATION = "MODE_REVERSE_SET_DESTINATION";
export const MODE_REVERSE_SET_PROTOCOL = "MODE_REVERSE_SET_PROTOCOL";
export const MODE_REVERSE_ERROR = "MODE_REVERSE_ERROR";
export const MODE_REVERSE_ADD_SERVER_CONFIG = "MODE_REVERSE_ADD_SERVER_CONFIG";

export interface ReverseState extends ModeState {
    protocol?: ReverseProxyProtocols;
    destination?: string;
    full_spec: string;
}

const defaultServerConfig: ReverseState = {
    active: false,
    protocol: ReverseProxyProtocols.HTTPS,
    destination: "",
    full_spec: "",
};

export interface ReverseServersState {
    servers: ReverseState[];
}

export const initialState: ReverseServersState = {
    servers: [defaultServerConfig],
};

export const addReverseServer = () => async (dispatch) => {
    dispatch({ type: MODE_REVERSE_ADD_SERVER_CONFIG });
};

export const getMode = (modes: ModesState): string[] => {
    const modesConfig: string[] = [];
    for (const server of modes.reverse.servers) {
        const mode = `reverse:${server.protocol}://${server.destination}`;
        modesConfig.push(...includeModeState(mode, server));
    }
    return modesConfig;
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

const getFullSpecReverse = (
    destination?: string,
    listen_host?: string,
    listen_port?: number,
    protocol?: string,
) => {
    let spec = `reverse:${destination}`;
    if (protocol) {
        spec = `reverse:${protocol}://${destination}`;
    }
    if (listen_host && listen_port) {
        spec = `${spec}@${listen_host}:${listen_port}`;
    }
    return spec;
};

const reverseReducer = (state = initialState, action): ReverseServersState => {
    switch (action.type) {
        case MODE_REVERSE_ADD_SERVER_CONFIG:
            return {
                servers: [...state.servers, defaultServerConfig],
            };
        case MODE_REVERSE_TOGGLE:
            return {
                servers: state.servers.map((server, index) =>
                    index === action.index
                        ? {
                              ...server,
                              active: !server.active,
                              error: undefined,
                          }
                        : server,
                ),
            };
        case MODE_REVERSE_SET_LISTEN_CONFIG:
            return {
                servers: state.servers.map((server, index) =>
                    index === action.index
                        ? {
                              ...server,
                              listen_port: action.port,
                              listen_host: action.host,
                              error: undefined,
                          }
                        : server,
                ),
            };
        case MODE_REVERSE_SET_DESTINATION:
            return {
                servers: state.servers.map((server, index) =>
                    index === action.index
                        ? {
                              ...server,
                              destination: action.destination,
                              error: undefined,
                          }
                        : server,
                ),
            };
        case MODE_REVERSE_SET_PROTOCOL:
            return {
                servers: state.servers.map((server, index) =>
                    index === action.index
                        ? {
                              ...server,
                              protocol: action.protocol,
                              error: undefined,
                          }
                        : server,
                ),
            };
        case UPDATE_STATE:
        case RECEIVE_STATE:
            if (action.data && action.data.servers) {
                const currentModeConfigs = getModesOfType(
                    "reverse",
                    action.data.servers,
                );

                let filteredServers = state.servers;

                if (currentModeConfigs.length > 0) {
                    filteredServers = state.servers.filter(
                        (server) => server !== defaultServerConfig,
                    );
                }

                const updatedServers: ReverseState[] = [];

                filteredServers.forEach((server) => {
                    const fullSpecConfig = getFullSpecReverse(
                        server.destination,
                        server.listen_host,
                        server.listen_port as number,
                        server.protocol,
                    );

                    const flag = !!currentModeConfigs.find(
                        (config) =>
                            getFullSpecReverse(
                                config.data,
                                config.listen_host,
                                config.listen_port as number,
                            ) === fullSpecConfig,
                    );

                    updatedServers.push({
                        active: flag,
                        protocol: server.protocol,
                        destination: server.destination,
                        listen_host: server.listen_host,
                        listen_port: Number(server.listen_port),
                        full_spec: fullSpecConfig,
                        error: undefined,
                    });
                });

                for (const config of currentModeConfigs) {
                    const [protocol, destination] = config.data.split("://");
                    const fullSpecConfig = getFullSpecReverse(
                        config.data,
                        config.listen_host,
                        config.listen_port as number,
                    );
                    if (
                        !updatedServers.find(
                            (server) => server.full_spec === fullSpecConfig,
                        )
                    ) {
                        updatedServers.push({
                            active: true,
                            protocol: protocol as ReverseProxyProtocols,
                            destination,
                            listen_host: config.listen_host,
                            listen_port: Number(config.listen_port),
                            full_spec: fullSpecConfig,
                            error: undefined,
                        });
                    }
                }

                return {
                    servers: updatedServers,
                };
            }
            return state;

        case MODE_REVERSE_ERROR:
            return {
                servers: state.servers.map((server, index) =>
                    index === action.index
                        ? {
                              ...server,
                              error: action.error,
                          }
                        : server,
                ),
            };
        default:
            return state;
    }
};

export default reverseReducer;
