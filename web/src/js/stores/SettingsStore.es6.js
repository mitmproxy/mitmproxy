class _SettingsStore extends EventEmitter {
    constructor() {
        super();

        //FIXME: What do we do if we haven't requested anything from the server yet?
        this.settings = {
            version: "0.12",
            showEventLog: true
        }; 
    }
    getAll() {
        return this.settings;
    }
    handle(action) {
        switch (action.actionType) {
            case ActionTypes.SETTINGS_UPDATE:
                this.settings = action.settings;
                this.emit("change");
                break;
            default:
                return;
        }
    }
}
var SettingsStore = new _SettingsStore();
AppDispatcher.register(SettingsStore.handle.bind(SettingsStore));