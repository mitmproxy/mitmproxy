function LiveFlowStore() {
    return new LiveStore("flows");
}

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
    this.recalculate(this.store._list, filt, sortfun);
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