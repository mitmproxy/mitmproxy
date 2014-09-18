function FlowView(store, live) {
    EventEmitter.call(this);
    this._store = store;
    this.live = live;
    this.flows = [];

    this.add = this.add.bind(this);
    this.update = this.update.bind(this);

    if (live) {
        this._store.addListener(ActionTypes.ADD_FLOW, this.add);
        this._store.addListener(ActionTypes.UPDATE_FLOW, this.update);
    }
}

_.extend(FlowView.prototype, EventEmitter.prototype, {
    close: function () {
        this._store.removeListener(ActionTypes.ADD_FLOW, this.add);
        this._store.removeListener(ActionTypes.UPDATE_FLOW, this.update);
    },
    getAll: function () {
        return this.flows;
    },
    add: function (flow) {
        return this.update(flow);
    },
    add_bulk: function (flows) {
        //Treat all previously received updates as newer than the bulk update.
        //If they weren't newer, we're about to receive an update for them very soon.
        var updates = this.flows;
        this.flows = flows;
        updates.forEach(function(flow){
            this._update(flow);
        }.bind(this));
        this.emit("change");
    },
    _update: function(flow){
        var idx = _.findIndex(this.flows, function(f){
            return flow.id === f.id;
        });

        if(idx < 0){
            this.flows.push(flow);
        } else {
            this.flows[idx] = flow;
        }
    },
    update: function(flow){
        this._update(flow);
        this.emit("change");
    },
});


function _FlowStore() {
    EventEmitter.call(this);
}
_.extend(_FlowStore.prototype, EventEmitter.prototype, {
    getView: function (since) {
        var view = new FlowView(this, !since);

        $.getJSON("/static/flows.json", function(flows){
           flows = flows.concat(_.cloneDeep(flows)).concat(_.cloneDeep(flows));
           var id = 1;
           flows.forEach(function(flow){
               flow.id = "uuid-"+id++;
           })
           view.add_bulk(flows); 

        });

        return view;
    },
    handle: function (action) {
        switch (action.type) {
            case ActionTypes.ADD_FLOW:
            case ActionTypes.UPDATE_FLOW:
                this.emit(action.type, action.data);
                break;
            default:
                return;
        }
    }
});


var FlowStore = new _FlowStore();
AppDispatcher.register(FlowStore.handle.bind(FlowStore));
