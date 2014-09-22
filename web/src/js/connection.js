function _Connection(url) {
    this.url = url;
}
_Connection.prototype.init = function () {
    this.openWebSocketConnection();
};
_Connection.prototype.openWebSocketConnection = function () {
    this.ws = new WebSocket(this.url.replace("http", "ws"));
    var ws = this.ws;

    ws.onopen = this.onopen.bind(this);
    ws.onmessage = this.onmessage.bind(this);
    ws.onerror = this.onerror.bind(this);
    ws.onclose = this.onclose.bind(this);
};
_Connection.prototype.onopen = function (open) {
    console.debug("onopen", this, arguments);
};
_Connection.prototype.onmessage = function (message) {
    //AppDispatcher.dispatchServerAction(...);
    var m = JSON.parse(message.data);
    AppDispatcher.dispatchServerAction(m);
};
_Connection.prototype.onerror = function (error) {
    EventLogActions.add_event("WebSocket Connection Error.");
    console.debug("onerror", this, arguments);
};
_Connection.prototype.onclose = function (close) {
    EventLogActions.add_event("WebSocket Connection closed.");
    console.debug("onclose", this, arguments);
};

var Connection = new _Connection(location.origin + "/updates");
