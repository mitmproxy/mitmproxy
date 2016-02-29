import $ from "jquery";
import _ from "lodash";
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

export var SettingsActions = {
    update: function (settings) {

        $.ajax({
            type: "PUT",
            url: "/settings",
            contentType: 'application/json',
            data: JSON.stringify(settings)
        });

        /*
        //Facebook Flux: We do an optimistic update on the client already.
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.SETTINGS_STORE,
            cmd: StoreCmds.UPDATE,
            data: settings
        });
        */
    }
};

var EventLogActions_event_id = 0;
export var EventLogActions = {
    add_event: function (message) {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.EVENT_STORE,
            cmd: StoreCmds.ADD,
            data: {
                message: message,
                level: "web",
                id: "viewAction-" + EventLogActions_event_id++
            }
        });
    }
};

export var FlowActions = {
    accept: function (flow) {
        $.post("/flows/" + flow.id + "/accept");
    },
    accept_all: function(){
        $.post("/flows/accept");
    },
    "delete": function(flow){
        $.ajax({
            type:"DELETE",
            url: "/flows/" + flow.id
        });
    },
    duplicate: function(flow){
        $.post("/flows/" + flow.id + "/duplicate");
    },
    replay: function(flow){
        $.post("/flows/" + flow.id + "/replay");
    },
    revert: function(flow){
        $.post("/flows/" + flow.id + "/revert");
    },
    update: function (flow, nextProps) {
        /*
        //Facebook Flux: We do an optimistic update on the client already.
        var nextFlow = _.cloneDeep(flow);
        _.merge(nextFlow, nextProps);
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.FLOW_STORE,
            cmd: StoreCmds.UPDATE,
            data: nextFlow
        });
        */
        $.ajax({
            type: "PUT",
            url: "/flows/" + flow.id,
            contentType: 'application/json',
            data: JSON.stringify(nextProps)
        });
    },
    clear: function(){
        $.post("/clear");
    }
};

export var Query = {
    SEARCH: "s",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e"
};