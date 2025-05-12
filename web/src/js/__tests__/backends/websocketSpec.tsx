import WebSocketBackend from "../../backends/websocket";
import fetchMock, { MockResponseInit } from "jest-fetch-mock";
import { waitFor } from "../test-utils";
import * as connectionActions from "../../ducks/connection";
import { UnknownAction } from "@reduxjs/toolkit";
import {
    EventLogItem,
    LogLevel,
    EVENTS_ADD,
    EVENTS_RECEIVE,
} from "../../ducks/eventLog";
import { OPTIONS_RECEIVE } from "../../ducks/options";
import { FLOWS_RECEIVE } from "../../ducks/flows";
import { STATE_RECEIVE } from "../../ducks/backendState";

beforeEach(() => {
    fetchMock.enableMocks();
    fetchMock.mockClear();
    const WebSocketOrig = WebSocket;
    // @ts-expect-error jest mock stuff
    jest.spyOn(global, "WebSocket").mockImplementation(() => ({
        addEventListener: () => 0,
        send: () => 0,
        readyState: WebSocketOrig.CONNECTING,
    }));
    // @ts-expect-error jest mock stuff
    global.WebSocket.OPEN = WebSocketOrig.OPEN;
    // @ts-expect-error jest mock stuff
    global.WebSocket.CONNECTING = WebSocketOrig.CONNECTING;
});

describe("websocket backend", () => {
    test("message queueing", async () => {
        let resolve;
        const events: Promise<MockResponseInit> = new Promise((r) => {
            resolve = r;
        });
        const never = async () => new Promise<MockResponseInit>(() => {});
        fetchMock.mockOnceIf("./state", never);
        fetchMock.mockOnceIf("./flows", never);
        fetchMock.mockOnceIf("./events", () => events);
        fetchMock.mockOnceIf("./options", never);

        const actions: Array<UnknownAction> = [];
        const backend = new WebSocketBackend({
            dispatch: (e) => actions.push(e),
        });

        backend.sendMessage({ type: "unknown" });
        expect(backend.messageQueue.length).toBe(1);
        // @ts-expect-error jest mock stuff
        backend.socket.readyState = WebSocket.OPEN;
        backend.onOpen();
        expect(backend.messageQueue.length).toBe(0);

        backend.sendMessage({ type: "unknown" });
        expect(backend.messageQueue.length).toBe(0);

        let payload: EventLogItem = {
            message: "test",
            level: LogLevel.debug,
            id: "123",
        };
        backend.onMessage({
            type: "events/add",
            payload,
        });

        expect(actions).toEqual([connectionActions.startFetching()]);
        actions.length = 0;

        resolve("[]");
        await waitFor(() =>
            expect(actions).toEqual([EVENTS_RECEIVE([]), EVENTS_ADD(payload)]),
        );
        actions.length = 0;
    });

    test("basic", async () => {
        fetchMock.mockOnceIf("./state", "{}");
        fetchMock.mockOnceIf("./flows", "[]");
        fetchMock.mockOnceIf("./events", "[]");
        fetchMock.mockOnceIf("./options", "{}");

        const actions: Array<UnknownAction> = [];
        const backend = new WebSocketBackend({
            dispatch: (e) => actions.push(e),
        });

        backend.onOpen();

        await waitFor(() =>
            expect(actions).toEqual([
                connectionActions.startFetching(),
                // @ts-expect-error mocked
                STATE_RECEIVE({}),
                FLOWS_RECEIVE([]),
                EVENTS_RECEIVE([]),
                // @ts-expect-error mocked
                OPTIONS_RECEIVE({}),
                connectionActions.connectionEstablished(),
            ]),
        );

        actions.length = 0;
        backend.onMessage({
            type: "events/add",
            payload: {
                id: "42",
                message: "test",
                level: LogLevel.info,
            } as EventLogItem,
        });
        expect(actions).toEqual([
            EVENTS_ADD({ id: "42", level: LogLevel.info, message: "test" }),
        ]);
        actions.length = 0;

        fetchMock.mockOnceIf("./events", "[]");
        backend.onMessage({
            type: "events/reset",
        });
        await waitFor(() =>
            expect(actions).toEqual([
                EVENTS_RECEIVE([]),
                connectionActions.connectionEstablished(),
            ]),
        );
        actions.length = 0;
        expect(fetchMock.mock.calls).toHaveLength(5);

        console.error = jest.fn();
        backend.onClose(new CloseEvent("Connection closed"));
        expect(console.error).toHaveBeenCalledTimes(1);
        expect(actions[0].type).toBe(connectionActions.connectionError.type);
        actions.length = 0;

        backend.onError(null);
        expect(console.error).toHaveBeenCalledTimes(2);

        jest.restoreAllMocks();
    });

    test("onMessage handling", async () => {
        fetchMock.mockOnceIf("./flows", "[]");
        fetchMock.mockOnceIf("./events", "[]");
        // Not useful, only for coverage
        const backend = new WebSocketBackend({ dispatch: () => {} });
        backend.onMessage({ type: "flows/add" });
        backend.onMessage({ type: "flows/update" });
        backend.onMessage({ type: "flows/remove" });
        backend.onMessage({ type: "flows/reset" });
        backend.onMessage({ type: "events/add" });
        backend.onMessage({ type: "events/reset" });
        backend.onMessage({ type: "options/update" });
        backend.onMessage({ type: "state/update" });
        expect(fetchMock.mock.calls.length).toBe(2);
    });
});
