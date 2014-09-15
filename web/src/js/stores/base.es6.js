class EventEmitter {
	constructor() {
		this.listeners = {};
	}
	emit(event) {
		if (!(event in this.listeners)) {
			return;
		}
		this.listeners[event].forEach(function(listener) {
			listener(event, this);
		}.bind(this));
	}
	addListener(event, f) {
		this.listeners[event] = this.listeners[event] || [];
		this.listeners[event].push(f);
	}
	removeListener(event, f) {
		if (!(event in this.listeners)) {
			return false;
		}
		var index = this.listeners[event].indexOf(f);
		if (index >= 0) {
			this.listeners[event].splice(index, 1);
		}
	}
}