function EventEmitter() {
    this.listeners = {};
}
EventEmitter.prototype.emit = function (event) {
    if (!(event in this.listeners)) {
        return;
    }
    var args = Array.prototype.slice.call(arguments, 1);
    this.listeners[event].forEach(function (listener) {
        listener.apply(this, args);
    }.bind(this));
};
EventEmitter.prototype.addListener = function (event, f) {
    this.listeners[event] = this.listeners[event] || [];
    this.listeners[event].push(f);
};
EventEmitter.prototype.removeListener = function (event, f) {
    if (!(event in this.listeners)) {
        return false;
    }
    var index = this.listeners[event].indexOf(f);
    if (index >= 0) {
        this.listeners[event].splice(index, 1);
    }
};
