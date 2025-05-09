import { createSlice } from "@reduxjs/toolkit";

export enum ConnectionState {
    INIT = "CONNECTION_INIT",
    FETCHING = "CONNECTION_FETCHING", // WebSocket is established, but still fetching resources.
    ESTABLISHED = "CONNECTION_ESTABLISHED",
    ERROR = "CONNECTION_ERROR",
    OFFLINE = "CONNECTION_OFFLINE", // indicates that there is no live (websocket) backend.
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
            state.state = ConnectionState.FETCHING;
            state.message = undefined;
        },
        connectionEstablished: (state) => {
            state.state = ConnectionState.ESTABLISHED;
            state.message = undefined;
        },
        connectionError: (state, action) => {
            state.state = ConnectionState.ERROR;
            state.message = action.payload;
        },
        setOffline: (state) => {
            state.state = ConnectionState.OFFLINE;
            state.message = undefined;
        },
    },
});

export const {
    startFetching,
    connectionEstablished,
    connectionError,
    setOffline,
} = connectionSlice.actions;
export default connectionSlice.reducer;
