import localReducer, {
    fetchProcesses,
    initialState,
    setActive,
    setSelectedProcesses,
} from "../../../ducks/modes/local";
import {
    RECEIVE as STATE_RECEIVE,
    BackendState,
} from "../../../ducks/backendState";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { PayloadAction } from "@reduxjs/toolkit";

describe("localSlice", () => {
    beforeEach(() => {
        enableFetchMocks();
        fetchMock.resetMocks();
    });

    it("should have working setters", async () => {
        enableFetchMocks();
        const store = TStore();

        expect(store.getState().modes.local[0]).toEqual({
            active: false,
            selectedProcesses: "",
            currentProcesses: [
                {
                    is_visible: true,
                    executable: "curl.exe",
                    is_system: "false",
                    display_name: "curl",
                },
                {
                    is_visible: true,
                    executable: "http.exe",
                    is_system: "false",
                    display_name: "http",
                },
            ],
            isLoading: false,
        });

        const server = store.getState().modes.local[0];
        await store.dispatch(setActive({ value: true, server }));
        await store.dispatch(setSelectedProcesses({ value: "curl", server }));

        expect(store.getState().modes.local[0]).toEqual({
            active: true,
            selectedProcesses: "curl",
            currentProcesses: [
                {
                    is_visible: true,
                    executable: "curl.exe",
                    is_system: "false",
                    display_name: "curl",
                },
                {
                    is_visible: true,
                    executable: "http.exe",
                    is_system: "false",
                    display_name: "http",
                },
            ],
            isLoading: false,
        });

        expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it("should handle error when setting local mode", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.local[0];
        await store.dispatch(setActive({ value: true, server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.local[0].error).toBe("invalid spec");
    });

    it("should handle error when setting processes", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.local[0];
        await store.dispatch(setSelectedProcesses({ value: "curl", server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.local[0].error).toBe("invalid spec");
    });

    it("should handle RECEIVE_STATE with an active local proxy", () => {
        const action = {
            type: STATE_RECEIVE.type,
            payload: {
                servers: {
                    "local:curl": {
                        description: "Local redirector",
                        full_spec: "local:curl",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [],
                        type: "local",
                    },
                },
            },
        } as PayloadAction<Partial<BackendState>>;
        const newState = localReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: true,
                selectedProcesses: "curl",
                currentProcesses: [],
                isLoading: false,
                ui_id: newState[0].ui_id,
            },
        ]);
    });

    it("should handle RECEIVE_STATE with no active local proxy", () => {
        const action = {
            type: STATE_RECEIVE.type,
            payload: {
                servers: {},
            },
        } as PayloadAction<Partial<BackendState>>;
        const newState = localReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: false,
                selectedProcesses: "",
                currentProcesses: [],
                isLoading: false,
                ui_id: newState[0].ui_id,
            },
        ]);
    });

    it("should handle fetchProcesses pending state", async () => {
        enableFetchMocks();
        fetchMock.mockResponseOnce(() => new Promise(() => {}));

        const store = TStore();

        store.dispatch(fetchProcesses());
        expect(store.getState().modes.local[0].isLoading).toBe(true);
    });

    it("should handle fetchProcesses fulfilled state", async () => {
        enableFetchMocks();
        const mockProcesses = [
            {
                is_visible: true,
                executable: "curl.exe",
                is_system: "false",
                display_name: "curl",
            },
            {
                is_visible: true,
                executable: "http.exe",
                is_system: "false",
                display_name: "http",
            },
        ];

        fetchMock.mockResponseOnce(JSON.stringify(mockProcesses));

        const store = TStore();

        await store.dispatch(fetchProcesses());

        expect(store.getState().modes.local[0].isLoading).toBe(false);
        expect(store.getState().modes.local[0].currentProcesses).toEqual(
            mockProcesses,
        );
        expect(fetchMock).toHaveBeenCalledWith("./processes", {
            credentials: "same-origin",
        });
    });

    it("should handle fetchProcesses rejected state", async () => {
        fetchMock.mockReject(new Error("Failed to fetch processes"));
        const store = TStore();

        await store.dispatch(fetchProcesses());

        expect(store.getState().modes.local[0].isLoading).toBe(false);
        expect(store.getState().modes.local[0].error).toBe(
            "Failed to fetch processes",
        );
        expect(fetchMock).toHaveBeenCalledWith("./processes", {
            credentials: "same-origin",
        });
    });
});
