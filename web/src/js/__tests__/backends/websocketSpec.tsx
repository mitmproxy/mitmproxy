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
