import WebSocketBackend from "../../backends/websocket";
import { enableFetchMocks } from "jest-fetch-mock";
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
