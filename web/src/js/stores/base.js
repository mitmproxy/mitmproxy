function EventEmitter() {"use strict";
        this.listeners = {};
    }
    EventEmitter.prototype.emit=function(event) {"use strict";
        if (!(event in this.listeners)) {
            return;
        }
        this.listeners[event].forEach(function(listener) {
            listener.apply(this, arguments);
        }.bind(this));
    };
    EventEmitter.prototype.addListener=function(event, f) {"use strict";
        this.listeners[event] = this.listeners[event] || [];
        this.listeners[event].push(f);
    };
    EventEmitter.prototype.removeListener=function(event, f) {"use strict";
        if (!(event in this.listeners)) {
            return false;
        }
        var index = this.listeners[event].indexOf(f);
        if (index >= 0) {
            this.listeners[event].splice(index, 1);
        }
    };
