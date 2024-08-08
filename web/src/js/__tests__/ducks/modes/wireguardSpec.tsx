/*import { enableFetchMocks } from "jest-fetch-mock";
import wireguardReducer, {
    initialState,
    setFilePath,
    setHost,
    setPort,
    toggleWireguard,
} from "../../../ducks/modes/wireguard";
import { TStore } from "../tutils";
import * as backendState from "../../../ducks/backendState";

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

    it("should dispatch MODE_WIREGUARD_SET_PORT and updateMode", async () => {
        enableFetchMocks();
        const store = TStore();

        await store.dispatch(setPort(8082));

        const state = store.getState().modes.wireguard;
        expect(state.listen_port).toBe(8082);
        expect(fetchMock).toHaveBeenCalled();
    });

    it("should dispatch MODE_WIREGUARD_SET_HOST and updateMode", async () => {
        enableFetchMocks();
        const store = TStore();

        await store.dispatch(setHost("localhost"));

        const state = store.getState().modes.wireguard;
        expect(state.listen_host).toBe("localhost");
        expect(fetchMock).toHaveBeenCalled();
    });

    it("should dispatch MODE_WIREGUARD_SET_FILE_PATH and updateMode", async () => {
        enableFetchMocks();
        const store = TStore();

        await store.dispatch(setFilePath("/path/to/local/wireguard.conf"));

        const state = store.getState().modes.wireguard;
        expect(state.file_path).toBe("/path/to/local/wireguard.conf");
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
        expect(newState.file_path).toBe("/path_example");
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
        expect(newState.listen_host).toBe(undefined);
        expect(newState.listen_port).toBe(undefined);
        expect(newState.file_path).toBe("");
    });

    it("should handle RECEIVE_STATE action with data.servers containing another mode", () => {
        const initialState = {
            active: false,
            listen_host: "localhost",
            listen_port: 8080,
            file_path: "/path_example",
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
        expect(newState.file_path).toBe(initialState.file_path);
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

    it("should handle error when setting port", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setPort(8082));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.wireguard.error).toBe("invalid spec");
    });

    it("should handle error when setting host", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setHost("localhost"));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.wireguard.error).toBe("invalid spec");
    });

    it("should handle error when setting file_path", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setFilePath("/path/to/local/wireguard.conf"));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.wireguard.error).toBe("invalid spec");
    });
});*/
/*
describe("getMode", () => {
    it("should return the correct mode string when active", () => {
        const modes = {
            wireguard: {
                active: true,
            },
        } as ModesState;
        const mode = getSpecs(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify(["wireguard"]));
    });

    it("should return an empty string when not active", () => {
        const modes = {
            wireguard: {
                active: false,
                file_path: "/path_example",
                listen_host: "localhost",
                listen_port: 8080,
            },
        } as ModesState;
        const mode = getSpecs(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });
});
*/

import wireguardReducer, {
    initialState,
    setListenHost,
    setListenPort,
    setActive,
    setFilePath,
} from "./../../../ducks/modes/wireguard";
import {
    RECEIVE as STATE_RECEIVE,
    BackendState,
} from "../../../ducks/backendState";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { PayloadAction } from "@reduxjs/toolkit";

describe("wireguardSlice", () => {
    it("should have working setters", async () => {
        enableFetchMocks();
        const store = TStore();

        expect(store.getState().modes.wireguard[0]).toEqual({
            active: false,
        });

        const server = store.getState().modes.wireguard[0];
        await store.dispatch(setActive({ value: false, server }));
        await store.dispatch(setListenHost({ value: "127.0.0.1", server }));
        await store.dispatch(setListenPort({ value: 4444, server }));
        await store.dispatch(setFilePath({ value: "/path/example", server }));

        expect(store.getState().modes.wireguard[0]).toEqual({
            active: false,
            listen_host: "127.0.0.1",
            listen_port: 4444,
            file_path: "/path/example",
        });

        expect(fetchMock).toHaveBeenCalledTimes(4);
    });

    it("should handle RECEIVE_STATE with an active wireguard proxy", () => {
        const action = {
            type: STATE_RECEIVE.type,
            payload: {
                servers: {
                    "wireguard:/path/example@localhost:8081": {
                        description: "WireGuard server",
                        full_spec: "wireguard:/path/example@localhost:8081",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [
                            ["127.0.0.1", 8081],
                            ["::1", 8081],
                        ],
                        type: "wireguard",
                    },
                },
            },
        } as PayloadAction<Partial<BackendState>>;
        const newState = wireguardReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: true,
                listen_host: "localhost",
                listen_port: 8081,
                file_path: "/path/example",
                ui_id: newState[0].ui_id,
            },
        ]);
    });

    it("should handle RECEIVE_STATE with no active wireguard proxy", () => {
        const action = {
            type: STATE_RECEIVE.type,
            payload: {
                servers: {},
            },
        } as PayloadAction<Partial<BackendState>>;
        const newState = wireguardReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: false,
                ui_id: newState[0].ui_id,
                file_path: "",
                listen_port: 51820,
            },
        ]);
    });
});