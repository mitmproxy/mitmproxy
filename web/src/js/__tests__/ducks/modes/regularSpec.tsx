import regularReducer, {
    initialState,
    setListenHost,
    setListenPort,
    setActive,
} from "./../../../ducks/modes/regular";
import {
    RECEIVE as STATE_RECEIVE,
    BackendState,
} from "../../../ducks/backendState";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { PayloadAction } from "@reduxjs/toolkit";

describe("regularSlice", () => {
    it("should have working setters", async () => {
        enableFetchMocks();
        const store = TStore();

        expect(store.getState().modes.regular[0]).toEqual({
            active: true,
        });

        const server = store.getState().modes.regular[0];
        await store.dispatch(setActive({ value: false, server }));
        await store.dispatch(setListenHost({ value: "127.0.0.1", server }));
        await store.dispatch(setListenPort({ value: 4444, server }));

        expect(store.getState().modes.regular[0]).toEqual({
            active: false,
            listen_host: "127.0.0.1",
            listen_port: 4444,
        });

        expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    it("should handle RECEIVE_STATE with an active regular proxy", () => {
        const action = {
            type: STATE_RECEIVE.type,
            payload: {
                servers: {
                    "regular@localhost:8081": {
                        description: "HTTP(S) proxy",
                        full_spec: "regular@localhost:8081",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [
                            ["127.0.0.1", 8081],
                            ["::1", 8081],
                        ],
                        type: "regular",
                    },
                },
            },
        } as PayloadAction<Partial<BackendState>>;
        const newState = regularReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: true,
                listen_host: "localhost",
                listen_port: 8081,
                ui_id: newState[0].ui_id,
            },
        ]);
    });

    it("should handle RECEIVE_STATE with no active regular proxy", () => {
        const action = {
            type: STATE_RECEIVE.type,
            payload: {
                servers: {},
            },
        } as PayloadAction<Partial<BackendState>>;
        const newState = regularReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: false,
                ui_id: newState[0].ui_id,
            },
        ]);
    });
});

// FIXME: move to __tests__/modes
/*
describe("getMode", () => {
    it("should return the correct mode string when active", () => {
        const modes = {
            regular: {
                active: true,
            },
        } as ModesState;
        const mode = getSpecs(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify(["regular"]));
    });

    it("should return an empty string when not active", () => {
        const modes = {
            regular: {
                active: false,
                listen_host: "localhost",
                listen_port: 8080,
            },
        } as ModesState;
        const mode = getSpecs(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });
});
*/
