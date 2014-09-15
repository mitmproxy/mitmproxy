class _Connection {
    constructor(root) {
        if (!root) {
            root = location.origin + "/api/v1";
        }
        this.root = root;
    }

    init() {
        this.openWebSocketConnection();
    }

    openWebSocketConnection() {
        this.ws = new WebSocket(this.root.replace("http", "ws") + "/ws");
        var ws = this.ws;

        ws.onopen = this.onopen.bind(this);
        ws.onmessage = this.onmessage.bind(this);
        ws.onerror = this.onerror.bind(this);
        ws.onclose = this.onclose.bind(this);
    }

    onopen(open) {
        console.log("onopen", this, arguments);
    }
    onmessage(message) {
        //AppDispatcher.dispatchServerAction(...);
        console.log("onmessage", this, arguments);
    }
    onerror(error) {
        console.log("onerror", this, arguments);
    }
    onclose(close) {
        console.log("onclose", this, arguments);
    }

}
var Connection = new _Connection();