function _SettingsStore() {
    EventEmitter.call(this);

    //FIXME: What do we do if we haven't requested anything from the server yet?
    this.settings = {
        version: "0.12",
        showEventLog: true,
        mode: "transparent",
    };
}
_.extend(_SettingsStore.prototype, EventEmitter.prototype, {
    getAll: function () {
        return this.settings;
    },
    handle: function (action) {
        switch (action.type) {
            case ActionTypes.UPDATE_SETTINGS:
                this.settings = action.settings;
                this.emit("change");
                break;
            default:
                return;
        }
    }
});

var SettingsStore = new _SettingsStore();
AppDispatcher.register(SettingsStore.handle.bind(SettingsStore));
