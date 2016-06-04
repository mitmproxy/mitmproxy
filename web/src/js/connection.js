import {ConnectionActions, EventLogActions} from "./actions.js";
import {AppDispatcher} from "./dispatcher.js";
import * as webSocketActions from "./ducks/websocket"
import * as eventLogActions from "./ducks/eventLog"

export default function Connection(url, dispatch) {
    if (url[0] === "/") {
        url = location.origin.replace("http", "ws") + url;
    }

    var ws = new WebSocket(url);
    ws.onopen = function () {
        dispatch(webSocketActions.connected())
        dispatch(eventLogActions.fetchLogEntries())
        ConnectionActions.open()
        //TODO: fetch stuff!
    };
    ws.onmessage = function (m) {
        var message = JSON.parse(m.data);
        AppDispatcher.dispatchServerAction(message);
        switch (message.type) {
            case eventLogActions.UPDATE_LOG:
                return dispatch(eventLogActions.updateLogEntries(message))
            default:
                console.warn("unknown message", message)
        }
    };
    ws.onerror = function () {
        ConnectionActions.error();
        EventLogActions.add_event("WebSocket connection error.");
    };
    ws.onclose = function () {
        ConnectionActions.close();
        EventLogActions.add_event("WebSocket connection closed.");
        dispatch(websocketActions.disconnected());
    };
    return ws;
}