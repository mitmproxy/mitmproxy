import {ConnectionActions} from "./actions.js";
import {AppDispatcher} from "./dispatcher.js";
import * as webSocketActions from "./ducks/websocket"
import * as eventLogActions from "./ducks/eventLog"
import * as flowActions from "./ducks/flows"
import * as settingsActions from './ducks/settings'

export default function Connection(url, dispatch) {
    if (url[0] === "/") {
        url = location.origin.replace("http", "ws") + url;
    }

    var ws = new WebSocket(url);
    ws.onopen = function () {
        dispatch(webSocketActions.connected())
        dispatch(settingsActions.fetchSettings())
        dispatch(eventLogActions.fetchData())
        dispatch(flowActions.fetchData())
        // workaround to make sure that our state is already available.
            .then(() => {
            console.log("flows are loaded now")
            ConnectionActions.open()
        })
    };
    ws.onmessage = function (m) {
        var message = JSON.parse(m.data);
        AppDispatcher.dispatchServerAction(message);
        switch (message.type) {
            case eventLogActions.WS_MSG_TYPE:
                return dispatch(eventLogActions.handleWsMsg(message))
            case flowActions.WS_MSG_TYPE:
                return dispatch(flowActions.handleWsMsg(message))
            case settingsActions.UPDATE_SETTINGS:
                return dispatch(settingsActions.handleWsMsg(message))
            default:
                console.warn("unknown message", message)
        }
    };
    ws.onerror = function () {
        ConnectionActions.error();
        dispatch(eventLogActions.add("WebSocket connection error."));
    };
    ws.onclose = function () {
        ConnectionActions.close();
        dispatch(eventLogActions.add("WebSocket connection closed."));
        dispatch(webSocketActions.disconnected());
    };
    return ws;
}
