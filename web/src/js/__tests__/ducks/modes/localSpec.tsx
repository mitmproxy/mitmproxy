import localReducer, {
    toggleLocal,
    addApplications,
    initialState,
    TOGGLE_LOCAL,
    ADD_APPLICATIONS,
    ERROR_LOCAL,
} from "../../../ducks/modes/local";
import { updateMode } from "../../../ducks/modes";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../../../ducks/options";

jest.mock("../../../ducks/modes", () => ({
    updateMode: jest.fn(),
}));

describe("localReducer", () => {
    it("should return the initial state", () => {
        const state = localReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should handle TOGGLE_LOCAL action", () => {
        const action = { type: TOGGLE_LOCAL };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(!initialState.active);
        expect(newState.error).toBeUndefined();
    });

    it("should handle ADD_APPLICATIONS action", () => {
        const applications = "app1, app2";
        const action = { type: ADD_APPLICATIONS, applications };
        const newState = localReducer(initialState, action);
        expect(newState.applications).toBe(applications);
        expect(newState.error).toBeUndefined();
    });

    it('should handle UPDATE_OPTIONS action with data.mode containing "local"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ["local", "local:app1"],
                },
            },
        };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.applications).toBe("app1");
        expect(newState.error).toBeUndefined();
    });
    
    it('should handle UPDATE_OPTIONS action with data.mode not containing "local"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ["othermode"],
                },
            },
        };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(false);
        expect(newState.applications).toBe("");
        expect(newState.error).toBeUndefined();
    });
    
    it("should handle ERROR_LOCAL action", () => {
        const error = "Some error occurred";
        const action = { type: ERROR_LOCAL, error };
        const newState = localReducer(initialState, action);
        expect(newState.error).toBe(error);
    });
});
