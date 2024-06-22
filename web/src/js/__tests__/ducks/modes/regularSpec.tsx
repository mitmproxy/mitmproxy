import regularReducer, {
    toggleRegular,
    getMode,
    initialState,
    MODE_REGULAR_TOGGLE,
} from "./../../../ducks/modes/regular";
import * as options from "../../../ducks/options";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

describe("regularReducer", () => {
    it("should return the initial state", () => {
        const state = regularReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should dispatch MODE_REGULAR_TOGGLE and updateMode", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.regular.active).toBe(true);
        await store.dispatch(toggleRegular());
        expect(store.getState().modes.regular.active).toBe(false);
        expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing "regular", an host and a port', () => {
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["regular@http:8081"],
                },
            },
        };
        const newState = regularReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.listen_host).toBe("http");
        expect(newState.listen_port).toBe(8081);
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing "regular" and a port', () => {
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["regular@8081"],
                },
            },
        };
        const newState = regularReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.listen_host).toBe(undefined);
        expect(newState.listen_port).toBe(8081);
    });
    it('should handle RECEIVE_OPTIONS action with data.mode containing "regular"', () => {
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["regular"],
                },
            },
        };
        const newState = regularReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.listen_host).toBe(undefined);
        expect(newState.listen_port).toBe(undefined);
    });
});

describe("getMode", () => {
    it("should return the correct mode string when active", () => {
        const modes = {
            regular: {
                active: true,
                name: "regular",
                listen_host: "localhost",
                listen_port: 8080,
            },
        };
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(
            JSON.stringify(["regular@localhost:8080"]),
        );
    });

    it("should return an empty string when not active", () => {
        const modes = {
            regular: {
                active: false,
                listen_host: "localhost",
                listen_port: 8080,
            },
        };
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });

    it("should return the correct mode string without listen_host and listen_port", () => {
        const modes = {
            regular: {
                active: true,
                name: "regular",
            },
        };
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify(["regular"]));
    });

    it("should return the correct mode string with listen_port and without listen_host", () => {
        const modes = {
            regular: {
                active: true,
                name: "regular",
                listen_port: 8080,
            },
        };
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(
            JSON.stringify(["regular@8080"]),
        );
    });
});
