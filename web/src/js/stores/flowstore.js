function FlowStore(endpoint) {
    this._views = [];
    this.reset();
}
_.extend(FlowStore.prototype, {
    add: function (flow) {
        this._pos_map[flow.id] = this._flow_list.length;
        this._flow_list.push(flow);
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].add(flow);
        }
    },
    update: function (flow) {
        this._flow_list[this._pos_map[flow.id]] = flow;
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].update(flow);
        }
    },
    remove: function (flow_id) {
        this._flow_list.splice(this._pos_map[flow_id], 1);
        this._build_map();
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].remove(flow_id);
        }
    },
    reset: function (flows) {
        this._flow_list = flows || [];
        this._build_map();
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].recalculate(this._flow_list);
        }
    },
    _build_map: function () {
        this._pos_map = {};
        for (var i = 0; i < this._flow_list.length; i++) {
            var flow = this._flow_list[i];
            this._pos_map[flow.id] = i;
        }
    },
    get: function (flow_id) {
        return this._flow_list[this._pos_map[flow_id]];
    }
});


function LiveFlowStore(endpoint) {
    FlowStore.call(this);
    this.updates_before_fetch = undefined;
    this._fetchxhr = false;
    this.endpoint = endpoint || "/flows";
    this.conn = new Connection(this.endpoint + "/updates");
    this.conn.onopen = this._onopen.bind(this);
    this.conn.onmessage = function (e) {
        var message = JSON.parse(e.data);
        this.handle_update(message.type, message.data);
    }.bind(this);
}
_.extend(LiveFlowStore.prototype, FlowStore.prototype, {
    close: function () {
        this.conn.close();
    },
    add: function (flow) {
        // Make sure that deferred adds don't add an element twice.
        if (!(flow.id in this._pos_map)) {
            FlowStore.prototype.add.call(this, flow);
        }
    },
    _onopen: function () {
        //Update stream openend, fetch list of flows.
        console.log("Update Connection opened, fetching flows...");
        this.fetch();
    },
    fetch: function () {
        if (this._fetchxhr) {
            this._fetchxhr.abort();
        }
        this._fetchxhr = $.getJSON(this.endpoint, this.handle_fetch.bind(this));
        this.updates_before_fetch = [];  // (JS: empty array is true)
    },
    handle_update: function (type, data) {
        console.log("LiveFlowStore.handle_update", type, data);

        if (type === "reset") {
            return this.fetch();
        }

        if (this.updates_before_fetch) {
            console.log("defer update", type, data);
            this.updates_before_fetch.push(arguments);
        } else {
            this[type](data);
        }
    },
    handle_fetch: function (data) {
        this._fetchxhr = false;
        console.log("Flows fetched.");
        this.reset(data.flows);
        var updates = this.updates_before_fetch;
        this.updates_before_fetch = false;
        for (var i = 0; i < updates.length; i++) {
            this.handle_update.apply(this, updates[i]);
        }
    },
});

function SortByInsertionOrder() {
    this.i = 0;
    this.map = {};
    this.key = this.key.bind(this);
}
SortByInsertionOrder.prototype.key = function (flow) {
    if (!(flow.id in this.map)) {
        this.i++;
        this.map[flow.id] = this.i;
    }
    return this.map[flow.id];
};

var default_sort = (new SortByInsertionOrder()).key;

function FlowView(store, filt, sortfun) {
    EventEmitter.call(this);
    filt = filt || function (flow) {
        return true;
    };
    sortfun = sortfun || default_sort;

    this.store = store;
    this.store._views.push(this);
    this.recalculate(this.store._flow_list, filt, sortfun);
}

_.extend(FlowView.prototype, EventEmitter.prototype, {
    close: function () {
        this.store._views = _.without(this.store._views, this);
    },
    recalculate: function (flows, filt, sortfun) {
        if (filt) {
            this.filt = filt;
        }
        if (sortfun) {
            this.sortfun = sortfun;
        }

        //Ugly workaround: Call .sortfun() for each flow once in order,
        //so that SortByInsertionOrder make sense.
        for (var i = 0; i < flows.length; i++) {
            this.sortfun(flows[i]);
        }

        this.flows = flows.filter(this.filt);
        this.flows.sort(function (a, b) {
            return this.sortfun(a) - this.sortfun(b);
        }.bind(this));
        this.emit("recalculate");
    },
    index: function (flow) {
        return _.sortedIndex(this.flows, flow, this.sortfun);
    },
    add: function (flow) {
        if (this.filt(flow)) {
            var idx = this.index(flow);
            if (idx === this.flows.length) { //happens often, .push is way faster.
                this.flows.push(flow);
            } else {
                this.flows.splice(idx, 0, flow);
            }
            this.emit("add", flow, idx);
        }
    },
    update: function (flow) {
        var idx;
        var i = this.flows.length;
        // Search from the back, we usually update the latest flows.
        while (i--) {
            if (this.flows[i].id === flow.id) {
                idx = i;
                break;
            }
        }

        if (idx === -1) { //not contained in list
            this.add(flow);
        } else if (!this.filt(flow)) {
            this.remove(flow.id);
        } else {
            if (this.sortfun(this.flows[idx]) !== this.sortfun(flow)) { //sortpos has changed
                this.remove(this.flows[idx]);
                this.add(flow);
            } else {
                this.flows[idx] = flow;
                this.emit("update", flow, idx);
            }
        }
    },
    remove: function (flow_id) {
        var i = this.flows.length;
        while (i--) {
            if (this.flows[i].id === flow_id) {
                this.flows.splice(i, 1);
                this.emit("remove", flow_id, i);
                break;
            }
        }
    }
});