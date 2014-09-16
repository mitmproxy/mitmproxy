var ActionTypes = {
    SETTINGS_UPDATE: "SETTINGS_UPDATE",
    EVENTLOG_ADD: "EVENTLOG_ADD"
};

var SettingsActions = {
    update:function(settings) {
        settings = _.merge({}, SettingsStore.getAll(), settings);
        //TODO: Update server.

        //Facebook Flux: We do an optimistic update on the client already.
        AppDispatcher.dispatchViewAction({
            actionType: ActionTypes.SETTINGS_UPDATE,
            settings: settings
        });
    }
};
