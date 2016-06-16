
import _ from "lodash";
import $ from "jquery";
import {EventEmitter} from 'events';
import {ActionTypes, StoreCmds} from "../actions.js";
import {AppDispatcher} from "../dispatcher.js";


function DictStore() {
    EventEmitter.call(this);
    this.reset();
}
_.extend(DictStore.prototype, EventEmitter.prototype, {
    update: function (dict) {
        _.merge(this.dict, dict);
        this.emit("recalculate");
    },
    reset: function (dict) {
        this.dict = dict || {};
        this.emit("recalculate");
    }
});

function LiveStoreMixin(type) {
    this.type = type;

    this._updates_before_fetch = undefined;
    this._fetchxhr = false;

    this.handle = this.handle.bind(this);
    AppDispatcher.register(this.handle);

    // Avoid double-fetch on startup.
    if (!(window.ws && window.ws.readyState === WebSocket.CONNECTING)) {
        this.fetch();
    }
}
_.extend(LiveStoreMixin.prototype, {
    handle: function (event) {
        if (event.type === ActionTypes.CONNECTION_OPEN) {
            return this.fetch();
        }
        if (event.type === this.type) {
            if (event.cmd === StoreCmds.RESET) {
                this.fetch(event.data);
            } else if (this._updates_before_fetch) {
                console.log("defer update", event);
                this._updates_before_fetch.push(event);
            } else {
                this[event.cmd](event.data);
            }
        }
    },
    close: function () {
        AppDispatcher.unregister(this.handle);
    },
    fetch: function (data) {
        console.log("fetch " + this.type);
        if (this._fetchxhr) {
            this._fetchxhr.abort();
        }
        this._updates_before_fetch = []; // (JS: empty array is true)
        if (data) {
            this.handle_fetch(data);
        } else {
            this._fetchxhr = $.getJSON("/" + this.type)
                .done(function (message) {
                    this.handle_fetch(message.data);
                }.bind(this))
                .fail(function () {
                    console.error("Could not fetch " + this.type)
                }.bind(this));
        }
    },
    handle_fetch: function (data) {
        this._fetchxhr = false;
        console.log(this.type + " fetched.", this._updates_before_fetch);
        this.reset(data);
        var updates = this._updates_before_fetch;
        this._updates_before_fetch = false;
        for (var i = 0; i < updates.length; i++) {
            this.handle(updates[i]);
        }
    },
});

function LiveDictStore(type) {
    DictStore.call(this);
    LiveStoreMixin.call(this, type);
}
_.extend(LiveDictStore.prototype, DictStore.prototype, LiveStoreMixin.prototype);
