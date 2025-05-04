import localReducer, {
    initialState,
    setActive,
    setSelectedProcesses,
} from "../../../ducks/modes/local";
import { STATE_UPDATE } from "../../../ducks/backendState";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

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
            ui_id: store.getState().modes.local[0].ui_id,
        });

        const server = store.getState().modes.local[0];
        await store.dispatch(setActive({ value: true, server }));
        await store.dispatch(setSelectedProcesses({ value: "curl", server }));

        expect(store.getState().modes.local[0]).toEqual({
            active: true,
            selectedProcesses: "curl",
            ui_id: store.getState().modes.local[0].ui_id,
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
        const action = STATE_UPDATE({
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
        });
        const newState = localReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: true,
                selectedProcesses: "curl",
                ui_id: newState[0].ui_id,
            },
        ]);
    });

    it("should handle RECEIVE_STATE with no active local proxy", () => {
        const action = STATE_UPDATE({ servers: {} });
        const newState = localReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: false,
                selectedProcesses: "",
                ui_id: newState[0].ui_id,
            },
        ]);
    });
});
