import {AppDispatcher} from "./dispatcher.js";

export var ActionTypes = {
    // Connection
    CONNECTION_OPEN: "connection_open",
    CONNECTION_CLOSE: "connection_close",
    CONNECTION_ERROR: "connection_error",

    // Stores
    SETTINGS_STORE: "settings",
    EVENT_STORE: "events",
    FLOW_STORE: "flows"
};

export var StoreCmds = {
    ADD: "add",
    UPDATE: "update",
    REMOVE: "remove",
    RESET: "reset"
};

export var ConnectionActions = {
    open: function () {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_OPEN
        });
    },
    close: function () {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_CLOSE
        });
    },
    error: function () {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_ERROR
        });
    }
};

export var Query = {
    SEARCH: "s",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e"
};
