class EventEmitter {
    constructor(){
        this._listeners = {};
    }
    emit(event){
        if(!(event in this._listeners)){
            return;
        }
        this._listeners[event].forEach(function (listener) {
            listener(event, this);
        }.bind(this));
    }
    addListener(event, f){
        this._listeners[event] = this._listeners[event] || [];
        this._listeners[event].push(f);
    }
    removeListener(event, f){
        if(!(event in this._listeners)){
            return false;
        }
        var index = this._listeners.indexOf(f);
        if (index >= 0) {
            this._listeners.splice(this._listeners.indexOf(f), 1);
        }
    }
}

var FLOW_CHANGED = "flow.changed";

class FlowStore extends EventEmitter{
    constructor() {
        super();
        this.flows = [];
        this._listeners = [];
    }

    getAll() {
        return this.flows;
    }

    emitChange() {
        return this.emit(FLOW_CHANGED);
    }

    addChangeListener(f) {
        this.addListener(FLOW_CHANGED, f);
    }

    removeChangeListener(f) {
        this.removeListener(FLOW_CHANGED, f);
    }
}

class DummyFlowStore extends FlowStore {
    constructor(flows) {
        super();
        this.flows = flows;
    }

    addFlow(f) {
        this.flows.push(f);
        this.emitChange();
    }
}


var SETTINGS_CHANGED = "settings.change";

class Settings extends EventEmitter {
    constructor(){
        super();
        this.settings = false;
    }

    getAll(){
        return this.settings;
    }

    emitChange() {
        return this.emit(SETTINGS_CHANGED);
    }

    addChangeListener(f) {
        this.addListener(SETTINGS_CHANGED, f);
    }

    removeChangeListener(f) {
        this.removeListener(SETTINGS_CHANGED, f);
    }
}

class DummySettings extends Settings {
    constructor(settings){
        super();
        this.settings = settings;
    }
    update(obj){
        _.merge(this.settings, obj);
        this.emitChange();
    }
}