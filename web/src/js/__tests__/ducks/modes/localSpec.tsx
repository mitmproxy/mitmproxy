import localReducer, {
    toggleLocal,
    setApplications,
    initialState,
    TOGGLE_LOCAL,
    SET_APPLICATIONS,
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

    it("should handle SET_APPLICATIONS action", () => {
        const applications = "app1, app2";
        const action = { type: SET_APPLICATIONS, applications };
        const newState = localReducer(initialState, action);
        expect(newState.applications).toBe(applications);
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
});
