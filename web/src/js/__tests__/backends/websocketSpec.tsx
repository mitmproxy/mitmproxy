import { enableFetchMocks } from "jest-fetch-mock";
import WebSocketBackend from "../../backends/websocket";
import { waitFor } from "../test-utils";
import * as connectionActions from "../../ducks/connection";
import { UnknownAction } from "@reduxjs/toolkit";

enableFetchMocks();

test("websocket backend", async () => {
    // @ts-expect-error jest mock stuff
    jest.spyOn(global, "WebSocket").mockImplementation(() => ({
        addEventListener: () => 0,
    }));

    fetchMock.mockOnceIf("./state", "{}");
    fetchMock.mockOnceIf("./flows", "[]");
    fetchMock.mockOnceIf("./events", "[]");
    fetchMock.mockOnceIf("./options", "{}");

    const actions: Array<UnknownAction> = [];
    const backend = new WebSocketBackend({ dispatch: (e) => actions.push(e) });

    backend.onOpen();

    await waitFor(() =>
        expect(actions).toEqual([
            connectionActions.startFetching(),
            {
                type: "STATE_RECEIVE",
                payload: {},
            },
            {
                type: "FLOWS_RECEIVE",
                cmd: "receive",
                data: [],
                resource: "flows",
            },
            {
                type: "EVENTS_RECEIVE",
                cmd: "receive",
                data: [],
                resource: "events",
            },
            {
                type: "OPTIONS_RECEIVE",
                cmd: "receive",
                data: {},
                resource: "options",
            },
            connectionActions.connectionEstablished(),
        ]),
    );

    actions.length = 0;
    backend.onMessage({
        resource: "events",
        cmd: "add",
        data: { id: "42", message: "test", level: "info" },
    });
    expect(actions).toEqual([
        {
            cmd: "add",
            data: { id: "42", level: "info", message: "test" },
            resource: "events",
            type: "EVENTS_ADD",
        },
    ]);
    actions.length = 0;

    fetchMock.mockOnceIf("./events", "[]");
    backend.onMessage({
        resource: "events",
        cmd: "reset",
    });
    await waitFor(() =>
        expect(actions).toEqual([
            {
                type: "EVENTS_RECEIVE",
                cmd: "receive",
                data: [],
                resource: "events",
            },
            connectionActions.connectionEstablished(),
        ]),
    );
    actions.length = 0;
    expect(fetchMock.mock.calls).toHaveLength(5);

    console.error = jest.fn();
    backend.onClose(new CloseEvent("Connection closed"));
    expect(console.error).toHaveBeenCalledTimes(1);
    expect(actions[0].type).toEqual(connectionActions.ConnectionState.ERROR);
    actions.length = 0;

    backend.onError(null);
    expect(console.error).toHaveBeenCalledTimes(2);

    jest.restoreAllMocks();
});

test("sendMessage should send message when WebSocket is open", () => {
    const backend = new WebSocketBackend({ dispatch: jest.fn() });

    const sendMessageSpy = jest.spyOn(backend as any, "sendMessage"); // trick to spy on sendMessage, which is private

    backend.socket = { readyState: WebSocket.OPEN, send: jest.fn() } as any;

    const name = "search";
    const expr = "~b boo";

    backend.updateFilter(name, expr);

    expect(sendMessageSpy).toHaveBeenCalledWith("flows", {
        cmd: "updateFilter",
        name,
        expr,
    });
});

test("sendMessage should queue messages when WebSocket is CONNECTING", () => {
    const backend = new WebSocketBackend({ dispatch: jest.fn() });

    backend.socket = {
        readyState: WebSocket.CONNECTING,
        send: jest.fn(),
    } as any;

    const messageQueueSpy = jest.spyOn(backend.messagesQueue, "push");

    const name = "search";
    const expr = "~b boo";
    backend.updateFilter(name, expr);

    expect(messageQueueSpy).toHaveBeenCalledWith(
        JSON.stringify({
            resource: "flows",
            cmd: "updateFilter",
            name: "search",
            expr: "~b boo",
        }),
    );
    expect(backend.messagesQueue).toHaveLength(1);
});

test("sendMessage should log an error if WebSocket is not CONNECTING or OPEN", () => {
    const backend = new WebSocketBackend({ dispatch: jest.fn() });

    backend.socket = {
        readyState: WebSocket.CLOSING,
        send: jest.fn(),
    } as any;

    const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

    const name = "search";
    const expr = "~b boo";
    backend.updateFilter(name, expr);

    expect(consoleErrorSpy).toHaveBeenCalledWith(
        "WebSocket is not open. Cannot send message:",
        "flows",
        { cmd: "updateFilter", name: "search", expr: "~b boo" },
    );

    consoleErrorSpy.mockRestore();
});
