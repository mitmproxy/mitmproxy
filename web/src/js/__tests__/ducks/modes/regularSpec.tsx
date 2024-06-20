import regularReducer, {
    toggleRegular,
    getMode,
    initialState,
    TOGGLE_REGULAR,
} from "./../../../ducks/modes/regular";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../../../ducks/options";
import { updateMode } from "../../../ducks/modes";

// Mock updateMode if needed
jest.mock("../../../ducks/modes", () => ({
    updateMode: jest.fn(),
}));

describe("regularReducer", () => {
    it("should return the initial state", () => {
        const state = regularReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should handle TOGGLE_REGULAR action", () => {
        const action = { type: TOGGLE_REGULAR };
        const newState = regularReducer(initialState, action);
        expect(newState.active).toBe(!initialState.active);
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing "regular"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ["regular"],
                },
            },
        };
        const newState = regularReducer(initialState, action);
        expect(newState.active).toBe(true);
    });

    it('should handle RECEIVE_OPTIONS action with data.mode not containing "regular"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ["othermode"],
                },
            },
        };
        const newState = regularReducer(initialState, action);
        expect(newState.active).toBe(false);
    });

    // Tests for getMode function
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
            expect(JSON.stringify(mode)).toBe(JSON.stringify(["regular@localhost:8080"]));
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
    });
});
