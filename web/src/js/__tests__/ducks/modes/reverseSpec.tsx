import reverseReducer, {
    toggleReverse,
    addProtocols,
    getMode,
    initialState,
    TOGGLE_REVERSE,
    ERROR_REVERSE,
    SET_PROTOCOLS,
} from "./../../../ducks/modes/reverse";
import { RECEIVE as RECEIVE_OPTIONS, UPDATE as UPDATE_OPTIONS } from "./../../../ducks/options";
import { updateMode } from "./../../../ducks/modes";

// Mock updateMode if needed
jest.mock("./../../../ducks/modes", () => ({
    updateMode: jest.fn(),
}));

describe('reverseReducer', () => {
    it('should return the initial state', () => {
        const state = reverseReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it('should handle TOGGLE_REVERSE action', () => {
        const action = { type: TOGGLE_REVERSE };
        const newState = reverseReducer(initialState, action);
        expect(newState.active).toBe(!initialState.active);
    });

    it('should handle ERROR_REVERSE action', () => {
        const error = 'Some error occurred';
        const action = { type: ERROR_REVERSE, error };
        const newState = reverseReducer(initialState, action);
        expect(newState.error).toBe(error);
    });

    it('should handle SET_PROTOCOLS action', () => {
        const protocolName = 'http';
        const action = { type: SET_PROTOCOLS, protocolName };
        const newState = reverseReducer(initialState, action);
        newState.protocols.forEach(protocol => {
            if (protocol.name === protocolName) {
                expect(protocol.isSelected).toBe(true);
            } else {
                expect(protocol.isSelected).toBe(false);
            }
        });
    });

    it('should handle RECEIVE_OPTIONS action with data.mode containing "reverse"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ['reverse:http'],
                },
            },
        };
        const newState = reverseReducer(initialState, action);
        expect(newState.active).toBe(true);
        const httpProtocol = newState.protocols.find(protocol => protocol.name === 'http');
        expect(httpProtocol?.isSelected).toBe(true);
    });

    it('should handle RECEIVE_OPTIONS action with data.mode not containing "reverse"', () => {
        const action = {
            type: RECEIVE_OPTIONS,
            data: {
                mode: {
                    value: ['othermode'],
                },
            },
        };
        const newState = reverseReducer(initialState, action);
        expect(newState.active).toBe(false);
    });

    // Tests for getMode function
    describe('getMode', () => {
        it('should return the correct mode string when active and a protocol is selected', () => {
            const modes = {
                reverse: {
                    ...initialState,
                    active: true,
                    protocols: initialState.protocols.map(protocol =>
                        protocol.name === 'http'
                            ? { ...protocol, isSelected: true }
                            : protocol
                    ),
                    listen_host: 'localhost',
                    listen_port: 8080,
                },
            };
            const mode = getMode(modes);
            expect(mode).toBe('reverse:http@localhost:8080');
        });

        it('should return an empty string when not active', () => {
            const modes = {
                reverse: {
                    ...initialState,
                    active: false,
                },
            };
            const mode = getMode(modes);
            expect(mode).toBe('');
        });

        it('should return the correct mode string without listen_host and listen_port', () => {
            const modes = {
                reverse: {
                    ...initialState,
                    active: true,
                    protocols: initialState.protocols.map(protocol =>
                        protocol.name === 'http'
                            ? { ...protocol, isSelected: true }
                            : protocol
                    ),
                },
            };
            const mode = getMode(modes);
            expect(mode).toBe('reverse:http');
        });
    });
});
