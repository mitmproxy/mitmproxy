function _Connection(root) {"use strict";
        if (!root) {
            root = location.origin + "/api/v1";
        }
        this.root = root;
    }
_Connection.prototype.init=function() {"use strict";
    this.openWebSocketConnection();
};
_Connection.prototype.openWebSocketConnection=function() {"use strict";
    this.ws = new WebSocket(this.root.replace("http", "ws") + "/ws");
    var ws = this.ws;

    ws.onopen = this.onopen.bind(this);
    ws.onmessage = this.onmessage.bind(this);
    ws.onerror = this.onerror.bind(this);
    ws.onclose = this.onclose.bind(this);
};
_Connection.prototype.onopen=function(open) {"use strict";
    console.log("onopen", this, arguments);
};
_Connection.prototype.onmessage=function(message) {"use strict";
    //AppDispatcher.dispatchServerAction(...);
    console.log("onmessage", this, arguments);
};
_Connection.prototype.onerror=function(error) {"use strict";
    console.log("onerror", this, arguments);
};
_Connection.prototype.onclose=function(close) {"use strict";
    console.log("onclose", this, arguments);
};

var Connection = new _Connection();
