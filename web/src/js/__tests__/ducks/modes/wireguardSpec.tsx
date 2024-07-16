import { enableFetchMocks } from "jest-fetch-mock";
import wireguardReducer, {
    getMode,
    initialState,
    toggleWireguard,
} from "../../../ducks/modes/wireguard";
import { TStore } from "../tutils";
import * as backendState from "../../../ducks/backendState";
import { ModesState } from "../../../ducks/modes";

describe("wireguardReducer", () => {
    it("should return the initial state", () => {
        const state = wireguardReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should dispatch MODE_WIREGUARD_TOGGLE and updateMode", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.wireguard.active).toBe(false);
        await store.dispatch(toggleWireguard());
        expect(store.getState().modes.wireguard.active).toBe(true);
        expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle RECEIVE_STATE action with data.servers containing "wireguard", an host and a port', () => {
        const action = {
            type: backendState.RECEIVE,
            data: {
                servers: [
                    {
                        wireguard_conf: null,
                        type: "wireguard",
                        description: "WireGuard server",
                        full_spec: "wireguard:/path_example@localhost:8081",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [],
                    },
                ],
            },
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.listen_host).toBe("localhost");
        expect(newState.listen_port).toBe(8081);
        expect(newState.path).toBe("/path_example");
    });

    it('should handle RECEIVE_STATE action with data.servers containing just "wireguard"', () => {
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
                        wireguard_conf: null,
                        type: "wireguard",
                        description: "WireGuard server",
                        full_spec: "wireguard",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [["0.0.0.0", 51820]],
                    },
                ],
            },
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.listen_host).toBe("");
        expect(newState.listen_port).toBe("");
        expect(newState.path).toBe("");
    });

    it("should handle RECEIVE_STATE action with data.servers containing another mode", () => {
        const initialState = {
            active: false,
            listen_host: "localhost",
            listen_port: 8080,
            path: "/path_example",
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
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(false);
        expect(newState.listen_host).toBe(initialState.listen_host);
        expect(newState.listen_port).toBe(initialState.listen_port);
        expect(newState.path).toBe(initialState.path);
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
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(initialState.active);
        expect(newState.listen_host).toBe(initialState.listen_host);
        expect(newState.listen_port).toBe(initialState.listen_port);
    });

    it("should handle MODE_WIREGUARD_ERROR action", () => {
        const initialState = {
            active: false,
        };
        const action = {
            type: "MODE_WIREGUARD_ERROR",
            error: "error message",
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.error).toBe("error message");
        expect(newState.active).toBe(false);
    });

    it("should handle error when toggling wireguard", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(toggleWireguard());

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.wireguard.error).toBe("invalid spec");
    });
});

describe("getMode", () => {
    it("should return the correct mode string when active", () => {
        const modes = {
            wireguard: {
                active: true,
            },
        } as ModesState;
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify(["wireguard"]));
    });

    it("should return an empty string when not active", () => {
        const modes = {
            wireguard: {
                active: false,
                path: "/path_example",
                listen_host: "localhost",
                listen_port: 8080,
            },
        } as ModesState;
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });
});
