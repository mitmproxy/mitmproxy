for(var EventEmitter____Key in EventEmitter){if(EventEmitter.hasOwnProperty(EventEmitter____Key)){_SettingsStore[EventEmitter____Key]=EventEmitter[EventEmitter____Key];}}var ____SuperProtoOfEventEmitter=EventEmitter===null?null:EventEmitter.prototype;_SettingsStore.prototype=Object.create(____SuperProtoOfEventEmitter);_SettingsStore.prototype.constructor=_SettingsStore;_SettingsStore.__superConstructor__=EventEmitter;
    function _SettingsStore() {"use strict";
        EventEmitter.call(this);

        //FIXME: What do we do if we haven't requested anything from the server yet?
        this.settings = {
            version: "0.12",
            showEventLog: true,
            mode: "transparent",
        }; 
    }
    _SettingsStore.prototype.getAll=function() {"use strict";
        return this.settings;
    };
    _SettingsStore.prototype.handle=function(action) {"use strict";
        switch (action.actionType) {
            case ActionTypes.SETTINGS_UPDATE:
                this.settings = action.settings;
                this.emit("change");
                break;
            default:
                return;
        }
    };

var SettingsStore = new _SettingsStore();
AppDispatcher.register(SettingsStore.handle.bind(SettingsStore));
