const PayloadSources = {
    VIEW_ACTION: "VIEW_ACTION",
    SERVER_ACTION: "SERVER_ACTION"
};


    function Dispatcher() {"use strict";
        this.callbacks = [];
    }
    Dispatcher.prototype.register=function(callback) {"use strict";
        this.callbacks.push(callback);
    };
    Dispatcher.prototype.unregister=function(callback) {"use strict";
        var index = this.callbacks.indexOf(f);
        if (index >= 0) {
            this.callbacks.splice(this.callbacks.indexOf(f), 1);
        }
    };
    Dispatcher.prototype.dispatch=function(payload) {"use strict";
        console.debug("dispatch", payload);
        this.callbacks.forEach(function(callback)  {
            callback(payload);
        });
    };


AppDispatcher = new Dispatcher();
AppDispatcher.dispatchViewAction = function(action) {
    action.actionSource = PayloadSources.VIEW_ACTION;
    this.dispatch(action);
};
AppDispatcher.dispatchServerAction = function(action) {
    action.actionSource = PayloadSources.SERVER_ACTION;
    this.dispatch(action);
};
