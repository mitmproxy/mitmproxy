class _SettingsStore extends EventEmitter {
	constructor() {
		/*jshint validthis: true */
		super();
		this.settings = { version: "0.12", showEventLog: true }; //FIXME: Need to get that from somewhere.
	}
	getSettings() {
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


var SettingsMixin = {
	getInitialState(){
		return {
			settings: SettingsStore.getSettings()
		};
	},
    componentDidMount(){
        SettingsStore.addListener("change", this._onSettingsChange);
    },
    componentWillUnmount(){
        SettingsStore.removeListener("change", this._onSettingsChange);
    },
    _onSettingsChange(){
    	this.setState({
    		settings: SettingsStore.getSettings()
    	});
    }
};