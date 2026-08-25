import { createSlice } from "@reduxjs/toolkit";

export enum ConnectionState {
    INIT = "CONNECTION_INIT",
    FETCHING = "CONNECTION_FETCHING", // WebSocket is established, but still fetching resources.
    ESTABLISHED = "CONNECTION_ESTABLISHED",
    ERROR = "CONNECTION_ERROR",
}

interface ConnState {
    state: ConnectionState;
    message?: string;
}

const defaultState: ConnState = {
    state: ConnectionState.INIT,
    message: undefined,
};

const connectionSlice = createSlice({
    name: "connection",
    initialState: defaultState,
    reducers: {
        startFetching: (state) => {
            if (state.state === ConnectionState.INIT) {
                state.state = ConnectionState.FETCHING;
            }
        },
        finishFetching: (state) => {
            if (state.state === ConnectionState.FETCHING) {
                state.state = ConnectionState.ESTABLISHED;
            }
        },
        connectionError: (state, action) => {
            state.state = ConnectionState.ERROR;
            state.message = action.payload;
        },
    },
});

export const { startFetching, finishFetching, connectionError } =
    connectionSlice.actions;
export default connectionSlice.reducer;
