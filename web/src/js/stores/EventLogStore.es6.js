class EventLogView extends EventEmitter {
	constructor(store, live){
		super();
		this._store = store;
		this.live = live;
		this.log = [];

		this.add = this.add.bind(this);

		if(live){
			this._store.addListener("new_entry", this.add);
		}
		
	}
	close() {
		this._store.removeListener("new_entry", this.add);
	}
	getAll() {
		return this.log;
	}

	add(entry){
		this.log.push(entry);
		this.emit("change");
	}
	add_bulk(messages){
		var log = messages;
		var last_id = log[log.length-1].id;
		var to_add = _.filter(this.log, entry => entry.id > last_id);
		this.log = log.concat(to_add);
		this.emit("change");
	}
}

class _EventLogStore extends EventEmitter {
	getView(since){
		var view = new EventLogView(this, !since);

		//TODO: Really do bulk retrieval of last messages.

		window.setTimeout(function(){
			view.add_bulk([
				{ id:1, message: "Hello World"},
				{ id:2, message: "I was already transmitted as an event."}
				]);
		}, 100);

		var id = 2;
		view.add({id:id++, message: "I was already transmitted as an event."});
		view.add({id:id++, message: "I was only transmitted as an event before the bulk was added.."});
		window.setInterval(function(){
			view.add({id: id++, message: "."});
		}, 1000);
		return view;
	}
	handle(action) {
		switch (action.actionType) {
			case ActionTypes.EVENTLOG_ADD:
				this.emit("new_message", action.message);
				break;
			default:
				return;
		}
	}
}
var EventLogStore = new _EventLogStore();
AppDispatcher.register(EventLogStore.handle.bind(EventLogStore));