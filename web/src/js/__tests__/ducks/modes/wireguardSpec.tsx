import { enableFetchMocks } from "jest-fetch-mock";
import wireguardReducer, { getMode, initialState, toggleWireguard } from "../../../ducks/modes/wireguard";
import { TStore } from "../tutils";
import * as options from "../../../ducks/options";


describe("wireguardReducer", ()=> {
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

    it('should handle RECEIVE_OPTIONS action with data.mode containing "wireguard", an host and a port', () => {
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["wireguard:/path_example@localhost:8081"],
                },
            },
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.listen_host).toBe("localhost");
        expect(newState.listen_port).toBe(8081);
        expect(newState.path).toBe("/path_example");
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing just "wireguard"', () => {
        const initialState = {
            active: false,
            listen_host: "localhost",
            listen_port: 8080,
        };
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["wireguard"],
                },
            },
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.listen_host).toBe("");
        expect(newState.listen_port).toBe("");
        expect(newState.path).toBe("");
    });

    it("should handle RECEIVE_OPTIONS action with data.mode containing another mode", () => {
        const initialState = {
            active: false,
            listen_host: "localhost",
            listen_port: 8080,
            path: "/path_example",
        };
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["local"],
                },
            },
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(false);
        expect(newState.listen_host).toBe(initialState.listen_host);
        expect(newState.listen_port).toBe(initialState.listen_port);
        expect(newState.path).toBe(initialState.path);
    });
})

describe("getMode", () => {
    it("should return the correct mode string when active", () => {
        const modes = {
            wireguard: {
                active: true,
            },
        };
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
        };
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });
});
