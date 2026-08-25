import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import reverseReducer, {
    initialState,
    setDestination,
    setProtocol,
    setActive,
    setListenHost,
    setListenPort,
    addServer,
    removeServer,
} from "../../../ducks/modes/reverse";
import { STATE_UPDATE } from "../../../ducks/backendState";
import { TStore } from "../tutils";
import { ReverseProxyProtocols } from "../../../backends/consts";

describe("reverseSlice", () => {
    it("should have working setters", async () => {
        enableFetchMocks();
        const store = TStore();

        expect(store.getState().modes.reverse[0]).toEqual({
            active: false,
            protocol: ReverseProxyProtocols.HTTPS,
            destination: "example.com",
            ui_id: store.getState().modes.reverse[0].ui_id,
        });

        const firstServer = store.getState().modes.reverse[0];
        await store.dispatch(setActive({ value: true, server: firstServer }));
        await store.dispatch(
            setListenHost({ value: "127.0.0.1", server: firstServer }),
        );
        await store.dispatch(
            setListenPort({ value: 4444, server: firstServer }),
        );
        await store.dispatch(
            setProtocol({
                value: ReverseProxyProtocols.HTTPS,
                server: firstServer,
            }),
        );
        await store.dispatch(
            setDestination({ value: "example.com:8085", server: firstServer }),
        );

        expect(store.getState().modes.reverse[0]).toEqual({
            active: true,
            listen_host: "127.0.0.1",
            listen_port: 4444,
            protocol: ReverseProxyProtocols.HTTPS,
            destination: "example.com:8085",
            ui_id: store.getState().modes.reverse[0].ui_id,
        });

        expect(fetchMock).toHaveBeenCalledTimes(5);
    });

    it("should handle error when setting reverse mode", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.reverse[0];
        await store.dispatch(setActive({ value: true, server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle error when setting listen port", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.reverse[0];
        await store.dispatch(setListenPort({ value: 4444, server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle error when setting listen host", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.reverse[0];
        await store.dispatch(setListenHost({ value: "localhost", server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle error when setting destination", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        const server = store.getState().modes.reverse[0];
        await store.dispatch(setDestination({ value: "example.com", server }));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.reverse[0].error).toBe("invalid spec");
    });

    it("should handle the addition of a new default reverse server", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.reverse.length).toBe(2);

        await store.dispatch(addServer());

        expect(store.getState().modes.reverse.length).toBe(3);
        expect(store.getState().modes.reverse[2]).toEqual({
            active: false,
            protocol: ReverseProxyProtocols.HTTPS,
            destination: "",
            ui_id: store.getState().modes.reverse[2].ui_id,
        });
    });

    it("should handle the deletion of an active reverse server", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.reverse.length).toBe(2);

        const firstServer = store.getState().modes.reverse[0];
        await store.dispatch(setActive({ value: true, server: firstServer }));

        const consoleSpy = jest
            .spyOn(console, "error")
            .mockImplementation(() => {});
        await store.dispatch(removeServer(store.getState().modes.reverse[0]));

        expect(store.getState().modes.reverse.length).toBe(1);
        expect(consoleSpy).toHaveBeenCalledWith(
            "servers should be deactivated before removal",
        );
        consoleSpy.mockRestore();
    });

    it("should handle RECEIVE_STATE with an active reverse proxy", () => {
        const action = STATE_UPDATE({
            servers: {
                "reverse:tls://example.com:8085@localhost:8080": {
                    description: "reverse proxy to tls://example.com:8085",
                    full_spec: "reverse:tls://example.com:8085@localhost:8080",
                    is_running: true,
                    last_exception: null,
                    listen_addrs: [
                        ["127.0.0.1", 8080],
                        ["::1", 8080, 0, 0],
                    ],
                    type: "reverse",
                },
            },
        });
        const newState = reverseReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: true,
                protocol: ReverseProxyProtocols.TLS,
                destination: "example.com:8085",
                listen_host: "localhost",
                listen_port: 8080,
                ui_id: newState[0].ui_id,
            },
        ]);
    });

    it("should handle RECEIVE_STATE with no active reverse proxy", () => {
        const action = STATE_UPDATE({ servers: {} });
        const newState = reverseReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: false,
                ui_id: newState[0].ui_id,
                destination: "",
                protocol: ReverseProxyProtocols.HTTPS,
            },
        ]);
    });

    it("should handle RECEIVE_STATE with an active reverse proxy and set protocol to HTTPS if destination is missing", () => {
        const action = STATE_UPDATE({
            servers: {
                "reverse:example.com:8085@localhost:8080": {
                    description: "reverse proxy to example.com:8085",
                    full_spec: "reverse:example.com:8085@localhost:8080",
                    is_running: true,
                    last_exception: null,
                    listen_addrs: [
                        ["127.0.0.1", 8080],
                        ["::1", 8080, 0, 0],
                    ],
                    type: "reverse",
                },
            },
        });
        const newState = reverseReducer(initialState, action);
        expect(newState).toEqual([
            {
                active: true,
                protocol: ReverseProxyProtocols.HTTPS,
                destination: "example.com:8085",
                listen_host: "localhost",
                listen_port: 8080,
                ui_id: newState[0].ui_id,
            },
        ]);
    });
});
