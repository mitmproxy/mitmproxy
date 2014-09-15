var ActionTypes = {
  SETTINGS_UPDATE: "SETTINGS_UPDATE",
  LOG_ADD: "LOG_ADD"
};

var SettingsActions = {
  update(settings) {
  	settings = _.merge({}, SettingsStore.getSettings(), settings);
    AppDispatcher.dispatchViewAction({
      actionType: ActionTypes.SETTINGS_UPDATE,
      settings: settings
    });
  }
};