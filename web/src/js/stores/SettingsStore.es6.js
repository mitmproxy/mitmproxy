class _SettingsStore extends EventEmitter {
	constructor() {
		super();
		this.settings = { version: "0.12", showEventLog: true }; //FIXME: Need to get that from somewhere.
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
