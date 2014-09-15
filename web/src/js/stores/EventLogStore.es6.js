class _EventLogStore extends EventEmitter {
	constructor() {
		/*jshint validthis: true */
		super();
		this.log = [];
	}
	getAll() {
		return this.log;
	}
	handle(action) {
		switch (action.actionType) {
			case ActionTypes.LOG_ADD:
				this.log.push(action.message);
				this.emit("change");
				break;
			default:
				return;
		}
	}
}
var EventLogStore = new _EventLogStore();
AppDispatcher.register(EventLogStore.handle.bind(EventLogStore));


var EventLogMixin = {
	getInitialState(){
		return {
			log: EventLog.getAll()
		};
	},
    componentDidMount(){
        SettingsStore.addListener("change", this._onEventLogChange);
    },
    componentWillUnmount(){
        SettingsStore.removeListener("change", this._onEventLogChange);
    },
    _onEventLogChange(){
    	this.setState({
    		log: EventLog.getAll()
    	});
    }
};