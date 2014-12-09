function Store() {
    this._views = [];
    this.reset();
}
_.extend(Store.prototype, {
    add: function (elem) {
        if (elem.id in this._pos_map) {
            return;
        }

        this._pos_map[elem.id] = this._list.length;
        this._list.push(elem);
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].add(elem);
        }
    },
    update: function (elem) {
        if (!(elem.id in this._pos_map)) {
            return;
        }

        this._list[this._pos_map[elem.id]] = elem;
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].update(elem);
        }
    },
    remove: function (elem_id) {
        if (!(elem.id in this._pos_map)) {
            return;
        }

        this._list.splice(this._pos_map[elem_id], 1);
        this._build_map();
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].remove(elem_id);
        }
    },
    reset: function (elems) {
        this._list = elems || [];
        this._build_map();
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].recalculate(this._list);
        }
    },
    _build_map: function () {
        this._pos_map = {};
        for (var i = 0; i < this._list.length; i++) {
            var elem = this._list[i];
            this._pos_map[elem.id] = i;
        }
    },
    get: function (elem_id) {
        return this._list[this._pos_map[elem_id]];
    },
    index: function(elem_id) {
        return this._pos_map[elem_id];
    }
});


function LiveStore(type) {
    Store.call(this);
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
_.extend(LiveStore.prototype, Store.prototype, {
    handle: function (event) {
        if (event.type === ActionTypes.CONNECTION_OPEN) {
            return this.fetch();
        }
        if (event.type === this.type) {
            if (event.cmd === StoreCmds.RESET) {
                this.fetch();
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
    fetch: function () {
        console.log("fetch " + this.type);
        if (this._fetchxhr) {
            this._fetchxhr.abort();
        }
        this._fetchxhr = $.getJSON("/" + this.type, this.handle_fetch.bind(this));
        this._updates_before_fetch = [];  // (JS: empty array is true)
    },
    handle_fetch: function (data) {
        this._fetchxhr = false;
        console.log(this.type + " fetched.", this._updates_before_fetch);
        this.reset(data.list);
        var updates = this._updates_before_fetch;
        this._updates_before_fetch = false;
        for (var i = 0; i < updates.length; i++) {
            this.handle(updates[i]);
        }
    },
});


function FlowStore() {
    return new LiveStore(ActionTypes.FLOW_STORE);
}


function EventLogStore() {
    return new LiveStore(ActionTypes.EVENT_STORE);
}