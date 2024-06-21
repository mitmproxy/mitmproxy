import localReducer, {
    toggleLocal,
    setApplications,
    initialState,
    MODE_LOCAL_TOGGLE,
    MODE_LOCAL_SET_APPLICATIONS,
    getMode,
    sanitizeInput,
} from "../../../ducks/modes/local";
import { RECEIVE as RECEIVE_OPTIONS } from "../../../ducks/options";
import { TStore } from "../tutils";

jest.mock("../../../ducks/modes", () => ({
    updateMode: jest.fn(() => ({ success: true })),
}));

describe("localReducer", () => {
    it("should return the initial state", () => {
        const state = localReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should handle MODE_LOCAL_TOGGLE action", () => {
        const action = { type: MODE_LOCAL_TOGGLE };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(!initialState.active);
        expect(newState.error).toBeUndefined();
    });

    it("should handle MODE_LOCAL_SET_APPLICATIONS action", () => {
        const applications = "app1, app2";
        const action = { type: MODE_LOCAL_SET_APPLICATIONS, applications };
        const newState = localReducer(initialState, action);
        expect(newState.applications).toBe(applications);
        expect(newState.error).toBeUndefined();
    });

    it("should dispatch MODE_LOCAL_TOGGLE and updateMode", async () => {
        const store = TStore();
        const mockUpdateMode = jest.fn(() => async () => ({ success: true }));

        await store.dispatch(toggleLocal(mockUpdateMode));

        const actions = store.getActions();
        expect(actions[0]).toEqual({ type: MODE_LOCAL_TOGGLE });
        expect(mockUpdateMode).toHaveBeenCalled();
    });

    it("should dispatch MODE_LOCAL_SET_APPLICATIONS and updateMode", async () => {
        const store = TStore();
        const mockUpdateMode = jest.fn(() => async () => ({ success: true }));

        await store.dispatch(setApplications("curl", mockUpdateMode));

        const actions = store.getActions();
        expect(actions[0]).toEqual({
            type: MODE_LOCAL_SET_APPLICATIONS,
            applications: "curl",
        });
        expect(mockUpdateMode).toHaveBeenCalled();
    });

    it("should handle RECEIVE_OPTIONS action", () => {
        const action = {
            type: RECEIVE_OPTIONS,
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
