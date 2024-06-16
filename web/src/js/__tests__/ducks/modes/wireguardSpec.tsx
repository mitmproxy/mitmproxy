import wireguardReducer, {
    toggleWireguard,
    getMode,
    initialState,
    TOGGLE_WIREGUARD,
    ERROR_WIREGUARD,
} from "./../../../ducks/modes/wireguard";
import { RECEIVE as RECEIVE_OPTIONS, UPDATE as UPDATE_OPTIONS } from "./../../../ducks/options";
import { updateMode } from "./../../../ducks/modes";

// Mock updateMode
jest.mock("./../../../ducks/modes", () => ({
    updateMode: jest.fn(),
}));

describe('wireguardReducer', () => {
    it('should return the initial state', () => {
        const state = wireguardReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it('should handle TOGGLE_WIREGUARD action', () => {
        const action = { type: TOGGLE_WIREGUARD };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(!initialState.active);
    });

    it('should handle ERROR_WIREGUARD action', () => {
        const error = 'Some error occurred';
        const action = { type: ERROR_WIREGUARD, error };
        const newState = wireguardReducer(initialState, action);
        expect(newState.error).toBe(error);
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing "wireguard"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ['wireguard'],
                },
            },
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(true);
    });

    it('should handle RECEIVE_OPTIONS action with data.mode not containing "wireguard"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ['othermode'],
                },
            },
        };
        const newState = wireguardReducer(initialState, action);
        expect(newState.active).toBe(false);
    });

    // Tests for getMode function
    describe('getMode', () => {
        it('should return the correct mode string when active', () => {
            const modes = {
                wireguard: {
                    ...initialState,
                    active: true,
                    listen_host: 'localhost',
                    listen_port: 51820,
                },
            };
            const mode = getMode(modes);
            expect(mode).toBe('wireguard@localhost:51820');
        });

        it('should return an empty string when not active', () => {
            const modes = {
                wireguard: {
                    ...initialState,
                    active: false,
                },
            };
            const mode = getMode(modes);
            expect(mode).toBe('');
        });

        it('should return the correct mode string without listen_host and listen_port', () => {
            const modes = {
                wireguard: {
                    ...initialState,
                    active: true,
                },
            };
            const mode = getMode(modes);
            expect(mode).toBe('wireguard');
        });
    });
});
