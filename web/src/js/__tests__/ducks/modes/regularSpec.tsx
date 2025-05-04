import regularReducer, {
    initialState,
    setListenHost,
    setListenPort,
    setActive,
} from "./../../../ducks/modes/regular";
import { STATE_UPDATE } from "../../../ducks/backendState";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

describe("regularSlice", () => {
    it("should have working setters", async () => {
        enableFetchMocks();
        const store = TStore();

        expect(store.getState().modes.regular[0]).toEqual({
            active: true,
            ui_id: store.getState().modes.regular[0].ui_id,
        });

        const server = store.getState().modes.regular[0];
        await store.dispatch(setActive({ value: false, server }));
        await store.dispatch(setListenHost({ value: "127.0.0.1", server }));
        await store.dispatch(setListenPort({ value: 4444, server }));

        expect(store.getState().modes.regular[0]).toEqual({
            active: false,
            listen_host: "127.0.0.1",
            listen_port: 4444,
            ui_id: store.getState().modes.regular[0].ui_id,
        });

        expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    it("should handle error when setting regular mode", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.regular[0];
        await store.dispatch(setActive({ value: false, server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.regular[0].error).toBe("invalid spec");
    });

    it("should handle error when setting listen port", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.regular[0];
        await store.dispatch(setListenPort({ value: 4444, server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.regular[0].error).toBe("invalid spec");
    });

    it("should handle error when setting listen host", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.regular[0];
        await store.dispatch(setListenHost({ value: "localhost", server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.regular[0].error).toBe("invalid spec");
    });

    it("should handle RECEIVE_STATE with an active regular proxy", () => {
        const action = STATE_UPDATE({
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
        });
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
        const action = STATE_UPDATE({ servers: {} });
        const newState = regularReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: false,
                ui_id: newState[0].ui_id,
            },
        ]);
    });
});
