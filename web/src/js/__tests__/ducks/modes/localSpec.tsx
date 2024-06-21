import localReducer, {
    toggleLocal,
    setApplications,
    initialState,
    MODE_LOCAL_TOGGLE,
    MODE_LOCAL_SET_APPLICATIONS,
    getMode,
    sanitizeInput,
} from "../../../ducks/modes/local";
import * as options from "../../../ducks/options";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

describe("localReducer", () => {
    it("should return the initial state", () => {
        const state = localReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should handle MODE_LOCAL_SET_APPLICATIONS action", () => {
        const applications = "app1, app2";
        const action = { type: MODE_LOCAL_SET_APPLICATIONS, applications };
        const newState = localReducer(initialState, action);
        expect(newState.applications).toBe(applications);
        expect(newState.error).toBeUndefined();
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
        const store = TStore();
        const mockUpdateMode = jest.fn(() => async () => ({ success: true }));

        await store.dispatch(setApplications("curl", mockUpdateMode));

        // FIXME
        /*const actions = store.getActions();
        expect(actions[0]).toEqual({
            type: MODE_LOCAL_SET_APPLICATIONS,
            applications: "curl",
        });
        expect(mockUpdateMode).toHaveBeenCalled();*/
    });

    it("should handle RECEIVE_OPTIONS action", () => {
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

    it("should return an empty array when local mode is defined but active is false", () => {
        const modes = {
            local: {
                active: false,
                applications: "",
            },
        };
        const result = getMode(modes);
        expect(result).toEqual([]);
    });

    it("should return local mode with multiple applications when active and multiple applications are present", () => {
        const modes = {
            local: {
                active: true,
                applications: "curl, wget",
            },
        };
        const result = getMode(modes);
        expect(result).toEqual(["local:curl, wget"]);
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
