import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import upstreamReducer, {
    initialState,
    setDestination,
    setActive,
    setListenHost,
    setListenPort,
} from "../../../ducks/modes/upstream";
import { STATE_UPDATE } from "../../../ducks/backendState";
import { TStore } from "../tutils";

describe("upstreamSlice", () => {
    it("should have working setters", async () => {
        enableFetchMocks();
        const store = TStore();

        expect(store.getState().modes.upstream[0]).toEqual({
            active: false,
            destination: "example.com",
            ui_id: store.getState().modes.upstream[0].ui_id,
        });

        await store.dispatch(
            setActive({
                value: true,
                server: store.getState().modes.upstream[0],
            }),
        );
        await store.dispatch(
            setListenHost({
                value: "127.0.0.1",
                server: store.getState().modes.upstream[0],
            }),
        );
        await store.dispatch(
            setListenPort({
                value: 4444,
                server: store.getState().modes.upstream[0],
            }),
        );
        await store.dispatch(
            setDestination({
                value: "example.com:8085",
                server: store.getState().modes.upstream[0],
            }),
        );

        expect(store.getState().modes.upstream[0]).toEqual({
            active: true,
            listen_host: "127.0.0.1",
            listen_port: 4444,
            destination: "example.com:8085",
            ui_id: store.getState().modes.upstream[0].ui_id,
        });

        expect(fetchMock).toHaveBeenCalledTimes(4);
    });

    it("should handle error when setting upstream mode", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.upstream[0];
        await store.dispatch(setActive({ value: true, server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.upstream[0].error).toBe("invalid spec");
    });

    it("should handle error when setting listen port", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.upstream[0];
        await store.dispatch(setListenPort({ value: 4444, server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.upstream[0].error).toBe("invalid spec");
    });

    it("should handle error when setting listen host", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.upstream[0];
        await store.dispatch(setListenHost({ value: "localhost", server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.upstream[0].error).toBe("invalid spec");
    });

    it("should handle error when setting destination", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.upstream[0];
        await store.dispatch(setDestination({ value: "example.com", server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.upstream[0].error).toBe("invalid spec");
    });

    it("should handle RECEIVE_STATE with an active upstream proxy", () => {
        const action = STATE_UPDATE({
            servers: {
                "upstream:https://example.com:8085@localhost:8080": {
                    description: "HTTP(S) proxy (upstream mode)",
                    full_spec:
                        "upstream:https://example.com:8085@localhost:8080",
                    is_running: true,
                    last_exception: null,
                    listen_addrs: [
                        ["127.0.0.1", 8080],
                        ["::1", 8080, 0, 0],
                    ],
                    type: "upstream",
                },
            },
        });
        const newState = upstreamReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: true,
                destination: "https://example.com:8085",
                listen_host: "localhost",
                listen_port: 8080,
                ui_id: newState[0].ui_id,
            },
        ]);
    });

    it("should handle RECEIVE_STATE with no active upstream proxy", () => {
        const action = STATE_UPDATE({ servers: {} });
        const newState = upstreamReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: false,
                ui_id: newState[0].ui_id,
                destination: "",
            },
        ]);
    });
});
