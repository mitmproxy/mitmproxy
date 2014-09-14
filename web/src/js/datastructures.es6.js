class EventEmitter {
    constructor(){
        this.listeners = {};
    }
    emit(event){
        if(!(event in this.listeners)){
            return;
        }
        this.listeners[event].forEach(function (listener) {
            listener(event, this);
        }.bind(this));
    }
    addListener(event, f){
        this.listeners[event] = this.listeners[event] || [];
        this.listeners[event].push(f);
    }
    removeListener(event, f){
        if(!(event in this.listeners)){
            return false;
        }
        var index = this.listeners.indexOf(f);
        if (index >= 0) {
            this.listeners.splice(this.listeners.indexOf(f), 1);
        }
    }
}

var FLOW_CHANGED = "flow.changed";

class FlowStore extends EventEmitter{
    constructor() {
        super();
        this.flows = [];
    }

    getAll() {
        return this.flows;
    }

    close(){
        console.log("FlowStore.close()");
        this.listeners = [];
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

    addFlow(flow) {
        this.flows.push(flow);
        this.emitChange();
    }
}


var SETTINGS_CHANGED = "settings.changed";

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