var ActionTypes = {
    //Settings
    UPDATE_SETTINGS: "update_settings",

    //EventLog
    ADD_EVENT: "add_event",

    //Flow
    ADD_FLOW: "add_flow",
    UPDATE_FLOW: "update_flow",
};

var SettingsActions = {
    update: function (settings) {
        settings = _.merge({}, SettingsStore.getAll(), settings);
        //TODO: Update server.

        //Facebook Flux: We do an optimistic update on the client already.
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.UPDATE_SETTINGS,
            settings: settings
        });
    }
};

var event_id = 0;
var EventLogActions = {
    add_event: function (message) {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.ADD_EVENT,
            data: {
                message: message,
                level: "web",
                id: "viewAction-" + event_id++
            }
        });
    }
};