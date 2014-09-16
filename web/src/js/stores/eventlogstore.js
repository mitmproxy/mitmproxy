//
// We have an EventLogView and an EventLogStore:
// The basic architecture is that one can request views on the event log
// from the store, which returns a view object and then deals with getting the data required for the view.
// The view object is accessed by React components and distributes updates etc.
//
// See also: components/EventLog.react.js

for(var EventEmitter____Key in EventEmitter){if(EventEmitter.hasOwnProperty(EventEmitter____Key)){EventLogView[EventEmitter____Key]=EventEmitter[EventEmitter____Key];}}var ____SuperProtoOfEventEmitter=EventEmitter===null?null:EventEmitter.prototype;EventLogView.prototype=Object.create(____SuperProtoOfEventEmitter);EventLogView.prototype.constructor=EventLogView;EventLogView.__superConstructor__=EventEmitter;
    function EventLogView(store, live) {"use strict";
        EventEmitter.call(this);
        this.$EventLogView_store = store;
        this.live = live;
        this.log = [];

        this.add = this.add.bind(this);

        if (live) {
            this.$EventLogView_store.addListener("new_entry", this.add);
        }
    }
    EventLogView.prototype.close=function() {"use strict";
        this.$EventLogView_store.removeListener("new_entry", this.add);
    };
    EventLogView.prototype.getAll=function() {"use strict";
        return this.log;
    };
    EventLogView.prototype.add=function(entry) {"use strict";
        this.log.push(entry);
        this.emit("change");
    };
    EventLogView.prototype.add_bulk=function(messages) {"use strict";
        var log = messages;
        var last_id = log[log.length - 1].id;
        var to_add = _.filter(this.log, function(entry)  {return entry.id > last_id;});
        this.log = log.concat(to_add);
        this.emit("change");
    };


for(EventEmitter____Key in EventEmitter){if(EventEmitter.hasOwnProperty(EventEmitter____Key)){_EventLogStore[EventEmitter____Key]=EventEmitter[EventEmitter____Key];}}_EventLogStore.prototype=Object.create(____SuperProtoOfEventEmitter);_EventLogStore.prototype.constructor=_EventLogStore;_EventLogStore.__superConstructor__=EventEmitter;function _EventLogStore(){"use strict";if(EventEmitter!==null){EventEmitter.apply(this,arguments);}}
    _EventLogStore.prototype.getView=function(since) {"use strict";
        var view = new EventLogView(this, !since);

        //TODO: Really do bulk retrieval of last messages.
        window.setTimeout(function() {
            view.add_bulk([{
                id: 1,
                message: "Hello World"
            }, {
                id: 2,
                message: "I was already transmitted as an event."
            }]);
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
        window.setInterval(function() {
            view.add({
                id: id++,
                message: "."
            });
        }, 1000);
        return view;
    };
    _EventLogStore.prototype.handle=function(action) {"use strict";
        switch (action.actionType) {
            case ActionTypes.EVENTLOG_ADD:
                this.emit("new_message", action.message);
                break;
            default:
                return;
        }
    };

var EventLogStore = new _EventLogStore();
AppDispatcher.register(EventLogStore.handle.bind(EventLogStore));
