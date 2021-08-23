import {enableFetchMocks} from "jest-fetch-mock";
import {TStore} from "../ducks/tutils";
import WebSocketBackend from "../../backends/websocket";
import {waitFor} from "../test-utils";
import * as connectionActions from "../../ducks/connection";

enableFetchMocks();

test("websocket backend", async () => {
    // @ts-ignore
    jest.spyOn(global, 'WebSocket').mockImplementation(() => ({addEventListener: () => 0}));

    fetchMock.mockOnceIf("./flows", "[]");
    fetchMock.mockOnceIf("./events", "[]");
    fetchMock.mockOnceIf("./options", "{}");
    const store = TStore();
    const backend = new WebSocketBackend(store);

    backend.onOpen();

    await waitFor(() => expect(store.getActions()).toEqual([
        connectionActions.startFetching(),
        {type: "FLOWS_RECEIVE", cmd: "receive", data: [], resource: "flows"},
        {type: "EVENTS_RECEIVE", cmd: "receive", data: [], resource: "events"},
        {type: "OPTIONS_RECEIVE", cmd: "receive", data: {}, resource: "options"},
        connectionActions.connectionEstablished(),
    ]))

    store.clearActions();
    backend.onMessage({
        "resource": "events",
        "cmd": "add",
        "data": {"id": "42", "message": "test", "level": "info"}
    });
    expect(store.getActions()).toEqual([{
        "cmd": "add",
        "data": {"id": "42", "level": "info", "message": "test"},
        "resource": "events",
        "type": "EVENTS_ADD"
    }]);
    store.clearActions();

    fetchMock.mockOnceIf("./events", "[]");
    backend.onMessage({
        "resource": "events",
        "cmd": "reset",
    });
    await waitFor(() => expect(store.getActions()).toEqual([
        {type: "EVENTS_RECEIVE", cmd: "receive", data: [], resource: "events"},
        connectionActions.connectionEstablished(),
    ]))
    store.clearActions()
    expect(fetchMock.mock.calls).toHaveLength(4);

    console.error = jest.fn();
    backend.onClose(new CloseEvent("Connection closed"));
    expect(console.error).toBeCalledTimes(1);
    expect(store.getActions()[0].type).toEqual(connectionActions.ConnectionState.ERROR);
    store.clearActions();

    backend.onError(null);
    expect(console.error).toBeCalledTimes(2);

    jest.restoreAllMocks();
});
