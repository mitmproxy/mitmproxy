//
// We have an EventLogView and an EventLogStore:
// The basic architecture is that one can request views on the event log
// from the store, which returns a view object and then deals with getting the data required for the view.
// The view object is accessed by React components and distributes updates etc.
//
// See also: components/EventLog.react.js
function EventLogView(store, live) {
    EventEmitter.call(this);
    this._store = store;
    this.live = live;
    this.log = [];

    this.add = this.add.bind(this);

    if (live) {
        this._store.addListener(ActionTypes.ADD_EVENT, this.add);
    }
}
_.extend(EventLogView.prototype, EventEmitter.prototype, {
    close: function () {
        this._store.removeListener(ActionTypes.ADD_EVENT, this.add);
    },
    getAll: function () {
        return this.log;
    },
    add: function (entry) {
        this.log.push(entry);
        this.emit("change");
    },
    add_bulk: function (messages) {
        var log = messages;
        var last_id = log[log.length - 1].id;
        var to_add = _.filter(this.log, function (entry) {
            return entry.id > last_id;
        });
        this.log = log.concat(to_add);
        this.emit("change");
    }
});


function _EventLogStore() {
    EventEmitter.call(this);
}
_.extend(_EventLogStore.prototype, EventEmitter.prototype, {
    getView: function (since) {
        var view = new EventLogView(this, !since);
        return view;
        /*
        //TODO: Really do bulk retrieval of last messages.
        window.setTimeout(function () {
            view.add_bulk([
                {
                    id: 1,
                    message: "Hello World"
                },
                {
                    id: 2,
                    message: "I was already transmitted as an event."
                }
            ]);
        }, 100);

        var id = 2;
        view.add({
            id: id++,
            message: "I was already transmitted as an event."
        });
        view.add({
            id: id++,
            message: "I was only transmitted as an event before the bulk was added.."
        });
        window.setInterval(function () {
            view.add({
                id: id++,
                message: "."
            });
        }, 1000);
        return view;
        */
    },
    handle: function (action) {
        switch (action.type) {
            case ActionTypes.ADD_EVENT:
                this.emit(ActionTypes.ADD_EVENT, action.data);
                break;
            default:
                return;
        }
    }
});


var EventLogStore = new _EventLogStore();
AppDispatcher.register(EventLogStore.handle.bind(EventLogStore));
