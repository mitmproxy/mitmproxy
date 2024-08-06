import { enableFetchMocks } from "jest-fetch-mock";
import reverseReducer, {
    addReverseServer,
    defaultReverseServerConfig,
    deleteReverse,
    getSpecs,
    initialState,
    setDestination,
    setListenConfig,
    setProtocol,
    toggleReverse,
} from "../../../ducks/modes/reverse";
import { TStore } from "../tutils";
import * as backendState from "../../../ducks/backendState";
import { ReverseProxyProtocols } from "../../../backends/consts";
import { ModesState } from "../../../ducks/modes";

describe("reverseReducer", () => {
    it("should return the initial state", () => {
        const state = reverseReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should dispatch MODE_REVERSE_TOGGLE and updateMode", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.reverse[0].active).toBe(false);
        expect(store.getState().modes.reverse[1].active).toBe(false);
        await store.dispatch(toggleReverse(0));
        expect(store.getState().modes.reverse[0].active).toBe(true);
        expect(store.getState().modes.reverse[1].active).toBe(false);
        expect(fetchMock).toHaveBeenCalled();
    });

    it("should dispatch MODE_REVERSE_ADD_SERVER_CONFIG", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.reverse.length).toBe(2);
        await store.dispatch(addReverseServer());
        expect(store.getState().modes.reverse.length).toBe(3);
        expect(store.getState().modes.reverse[2]).toBe(
            defaultReverseServerConfig,
        );
    });

    it("should dispatch MODE_REVERSE_DELETE and updateMode", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.reverse.length).toBe(2);
        await store.dispatch(deleteReverse(0));
        expect(store.getState().modes.reverse.length).toBe(1);
    });

    it('should handle RECEIVE_STATE action with initial UI state and data.servers containing "reverse", an host and a port and a destination"', () => {
        const action = {
            type: backendState.RECEIVE,
            data: {
                servers: [
                    {
                        type: "reverse",
                        description: "reverse proxy to tls://example.com:8085",
                        full_spec:
                            "reverse:tls://example.com:8085@localhost:8080",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [
                            ["127.0.0.1", 8080],
                            ["::1", 8080, 0, 0],
                        ],
                    },
                ],
            },
        };

        const initialState = [
            {
                active: false,
                protocol: ReverseProxyProtocols.HTTPS,
                destination: "example.com:8085",
                listen_host: "localhost",
                listen_port: 8082,
            }
        ];

        const newState = reverseReducer(initialState, action);
        expect(newState[0].active).toBe(false);
        expect(newState[0].protocol).toBe(ReverseProxyProtocols.HTTPS);
        expect(newState[0].destination).toBe("example.com:8085");
        expect(newState[0].listen_host).toBe("localhost");
        expect(newState[0].listen_port).toBe(8082);

        expect(newState[1].active).toBe(true);
        expect(newState[1].protocol).toBe(ReverseProxyProtocols.TLS);
        expect(newState[1].destination).toBe("example.com:8085");
        expect(newState[1].listen_host).toBe("localhost");
        expect(newState[1].listen_port).toBe(8080);
    });

    it("should handle RECEIVE_STATE action and set protocol to HTTPS if destination is missing", () => {
        const action = {
            type: backendState.RECEIVE,
            data: {
                servers: [
                    {
                        type: "reverse",
                        description: "reverse proxy to example.com:8085",
                        full_spec: "reverse:example.com:8085@localhost:8080",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [
                            ["127.0.0.1", 8080],
                            ["::1", 8080, 0, 0],
                        ],
                    },
                ],
            },
        };
        const newState = reverseReducer(initialState, action);

        expect(newState[0].active).toBe(true);
        expect(newState[0].protocol).toBe(ReverseProxyProtocols.HTTPS);
        expect(newState[0].destination).toBe("example.com:8085");
        expect(newState[0].listen_host).toBe("localhost");
        expect(newState[0].listen_port).toBe(8080);
    });

    it("should handle RECEIVE_STATE action with data.servers containing another mode", () => {
        const action = {
            type: backendState.RECEIVE,
            data: {
                servers: [
                    {
                        description: "Local redirector",
                        full_spec: "local",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [],
                        type: "local",
                    },
                ],
            },
        };
        const newState = reverseReducer(initialState, action);
        expect(newState[0].active).toBe(false);
        expect(newState[0].listen_host).toBe(initialState[0].listen_host);
        expect(newState[0].listen_port).toBe(initialState[0].listen_port);
    });

    it("should handle RECEIVE_STATE action without data.servers", () => {
        const action = {
            type: backendState.RECEIVE,
            data: {},
        };
        const newState = reverseReducer(initialState, action);
        expect(newState[0].active).toBe(initialState[0].active);
        expect(newState[0].listen_host).toBe(initialState[0].listen_host);
        expect(newState[0].listen_port).toBe(initialState[0].listen_port);
    });

    it("should handle MODE_REVERSE_ERROR action", () => {
        const action = {
            type: "MODE_REVERSE_ERROR",
            error: "error message",
            index: 0,
        };
        const newState = reverseReducer(initialState, action);
        expect(newState[0].error).toBe("error message");
        expect(newState[0].active).toBe(false);
    });

    it("should handle error when toggling reverse", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(toggleReverse(0));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle error when setting protocol", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setProtocol(ReverseProxyProtocols.HTTPS, 0));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle error when setting listen config", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setListenConfig(8082, "localhost", 0));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle error when setting destination", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setDestination("example.com:8085", 0));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle error when deleting single reverse mode", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(deleteReverse(0));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });
});

describe("getMode", () => {
    it("should return reverse mode with destination when active and protocol and destination are present", () => {
        const modes = {
            reverse: [
                {
                    active: true,
                    protocol: ReverseProxyProtocols.HTTPS,
                    destination: "example.com:8085",
                },
            ],
        } as ModesState;
        const result = getSpecs(modes);
        expect(result).toEqual(["reverse:https://example.com:8085"]);
    });

    it("should return an empty array when reverse mode is not active", () => {
        const modes = {
            reverse: [
                {
                    active: false,
                    protocol: ReverseProxyProtocols.HTTPS,
                    destination: "example.com:8085",
                },
            ],
        } as ModesState;
        const result = getSpecs(modes);
        expect(result).toEqual([]);
    });

    it("should return an empty string when there is a ui error", () => {
        const modes = {
            reverse: [
                {
                    active: false,
                    protocol: ReverseProxyProtocols.HTTPS,
                    destination: "example.com:8085",
                    error: "error reverse mode",
                },
            ],
        } as ModesState;
        const mode = getSpecs(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });
});
