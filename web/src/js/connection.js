
import {ConnectionActions, EventLogActions} from "./actions.js";
import {AppDispatcher} from "./dispatcher.js";

function Connection(url) {
    if (url[0] === "/") {
        url = location.origin.replace("http", "ws") + url;
    }

    var ws = new WebSocket(url);
    ws.onopen = function () {
        ConnectionActions.open();
    };
    ws.onmessage = function (message) {
        var m = JSON.parse(message.data);
        AppDispatcher.dispatchServerAction(m);
    };
    ws.onerror = function () {
        ConnectionActions.error();
        EventLogActions.add_event("WebSocket connection error.");
    };
    ws.onclose = function () {
        ConnectionActions.close();
        EventLogActions.add_event("WebSocket connection closed.");
    };
    return ws;
}

export default Connection;