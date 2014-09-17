const PayloadSources = {
    VIEW_ACTION: "VIEW_ACTION",
    SERVER_ACTION: "SERVER_ACTION"
};


function Dispatcher() {
    this.callbacks = [];
}
Dispatcher.prototype.register = function (callback) {
    this.callbacks.push(callback);
};
Dispatcher.prototype.unregister = function (callback) {
    var index = this.callbacks.indexOf(f);
    if (index >= 0) {
        this.callbacks.splice(this.callbacks.indexOf(f), 1);
    }
};
Dispatcher.prototype.dispatch = function (payload) {
    console.debug("dispatch", payload);
    this.callbacks.forEach(function (callback) {
        callback(payload);
    });
};


AppDispatcher = new Dispatcher();
AppDispatcher.dispatchViewAction = function (action) {
    action.actionSource = PayloadSources.VIEW_ACTION;
    this.dispatch(action);
};
AppDispatcher.dispatchServerAction = function (action) {
    action.actionSource = PayloadSources.SERVER_ACTION;
    this.dispatch(action);
};
