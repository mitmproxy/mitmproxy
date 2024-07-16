import { enableFetchMocks } from "jest-fetch-mock";
import reverseReducer, {
    getMode,
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

        expect(store.getState().modes.reverse.active).toBe(false);
        await store.dispatch(toggleReverse());
        expect(store.getState().modes.reverse.active).toBe(true);
        expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle RECEIVE_STATE action with data.servers containing "reverse", an host and a port and a destination"', () => {
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
        const newState = reverseReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.protocol).toBe("tls");
        expect(newState.destination).toBe("example.com:8085");
        expect(newState.listen_host).toBe("localhost");
        expect(newState.listen_port).toBe(8080);
    });

    it("should handle RECEIVE_STATE action with data.servers containing another mode", () => {
        const initialState = {
            active: false,
            listen_host: "localhost",
            listen_port: 8080,
        };
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
        expect(newState.active).toBe(false);
        expect(newState.listen_host).toBe(initialState.listen_host);
        expect(newState.listen_port).toBe(initialState.listen_port);
    });

    it("should handle RECEIVE_STATE action without data.servers", () => {
        const initialState = {
            active: false,
            listen_host: "localhost",
            listen_port: 8080,
        };
        const action = {
            type: backendState.RECEIVE,
            data: {},
        };
        const newState = reverseReducer(initialState, action);
        expect(newState.active).toBe(initialState.active);
        expect(newState.listen_host).toBe(initialState.listen_host);
        expect(newState.listen_port).toBe(initialState.listen_port);
    });

    it("should handle MODE_REVERSE_ERROR action", () => {
        const initialState = {
            active: false,
        };
        const action = {
            type: "MODE_REVERSE_ERROR",
            error: "error message",
        };
        const newState = reverseReducer(initialState, action);
        expect(newState.error).toBe("error message");
        expect(newState.active).toBe(false);
    });

    it("should handle error when toggling reverse", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(toggleReverse());

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse.error).toBe("invalid spec");
    });

    it("should handle error when setting protocol", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setProtocol(ReverseProxyProtocols.HTTPS));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse.error).toBe("invalid spec");
    });

    it("should handle error when setting listen config", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setListenConfig(8082, "localhost"));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse.error).toBe("invalid spec");
    });

    it("should handle error when setting destination", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setDestination("example.com:8085"));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse.error).toBe("invalid spec");
    });
});

describe("getMode", () => {
    it("should return reverse mode with destination when active and protocol and destination are present", () => {
        const modes = {
            reverse: {
                active: true,
                protocol: ReverseProxyProtocols.HTTPS,
                destination: "example.com:8085",
            },
        } as ModesState;
        const result = getMode(modes);
        expect(result).toEqual(["reverse:https://example.com:8085"]);
    });

    it("should return an empty array when reverse mode is not active", () => {
        const modes = {
            reverse: {
                active: false,
                protocol: ReverseProxyProtocols.HTTPS,
                destination: "example.com:8085",
            },
        } as ModesState;
        const result = getMode(modes);
        expect(result).toEqual([]);
    });

    it("should return an empty string when there is a ui error", () => {
        const modes = {
            reverse: {
                active: false,
                protocol: ReverseProxyProtocols.HTTPS,
                destination: "example.com:8085",
                error: "error reverse mode",
            },
        } as ModesState;
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });
});
