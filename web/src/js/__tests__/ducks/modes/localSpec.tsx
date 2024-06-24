import localReducer, {
    toggleLocal,
    setApplications,
    initialState,
    getMode,
    sanitizeInput,
} from "../../../ducks/modes/local";
import { toggleRegular } from "../../../ducks/modes/regular";
import * as options from "../../../ducks/options";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

describe("localReducer", () => {
    it("should return the initial state", () => {
        const state = localReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should dispatch MODE_LOCAL_TOGGLE and updateMode", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.local.active).toBe(false);
        await store.dispatch(toggleLocal());
        expect(store.getState().modes.local.active).toBe(true);
        expect(fetchMock).toHaveBeenCalled();
    });

    it("should dispatch MODE_LOCAL_SET_APPLICATIONS and updateMode", async () => {
        enableFetchMocks();
        const store = TStore();

        await store.dispatch(setApplications("curl"));

        const state = store.getState().modes.local;
        expect(state.applications).toEqual("curl");
        expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle UPDATE_OPTIONS action with data.mode not containing "local"', async () => {
        const store = TStore();

        await store.dispatch(setApplications("curl"));

        await store.dispatch(toggleRegular());

        expect(store.getState().modes.local.active).toBe(false);
        expect(store.getState().modes.regular.active).toBe(false);
        expect(store.getState().modes.local.applications).toBe("curl");
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing "local" and an application', () => {
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["local:curl"],
                },
            },
        };
        const newState = localReducer(undefined, action);
        expect(newState.active).toBe(true);
        expect(newState.applications).toBe("curl");
        expect(newState.error).toBeUndefined();
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing "local"', () => {
        const initialState = {
            active: false,
            applications: "curl",
        };
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["local"],
                },
            },
        };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.applications).toBe("");
        expect(newState.error).toBeUndefined();
    });

    it("should handle RECEIVE_OPTIONS action with data.mode containing another mode", () => {
        const initialState = {
            active: false,
            applications: "curl",
        };
        const action = {
            type: options.RECEIVE,
            data: {
                mode: {
                    value: ["regular"],
                },
            },
        };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(false);
        expect(newState.applications).toBe(initialState.applications);
    });
});

describe("getMode", () => {
    it("should return local mode with applications when active and applications are present", () => {
        const modes = {
            local: {
                active: true,
                applications: "curl",
            },
        };
        const result = getMode(modes);
        expect(result).toEqual(["local:curl"]);
    });

    it("should return local mode without applications when active and no applications are present", () => {
        const modes = {
            local: {
                active: true,
                applications: "",
            },
        };
        const result = getMode(modes);
        expect(result).toEqual(["local"]);
    });

    it("should return an empty array when local mode is not active", () => {
        const modes = {
            local: {
                active: false,
                applications: "curl",
            },
        };
        const result = getMode(modes);
        expect(result).toEqual([]);
    });
});

describe("sanitizeInput", () => {
    it("should remove trailing comma", () => {
        const input = "test,";
        const result = sanitizeInput(input);
        expect(result).toBe("test");
    });

    it("should return the same string if there is no trailing comma", () => {
        const input = "test";
        const result = sanitizeInput(input);
        expect(result).toBe(input);
    });

    it("should return an empty string if input is empty", () => {
        const input = "";
        const result = sanitizeInput(input);
        expect(result).toBe("");
    });

    it("should return an empty string if input is just a comma", () => {
        const input = ",";
        const result = sanitizeInput(input);
        expect(result).toBe("");
    });
});
