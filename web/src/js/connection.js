function _Connection(url) {
    this.url = url;
}
_Connection.prototype.init=function() {
    this.openWebSocketConnection();
};
_Connection.prototype.openWebSocketConnection=function() {
    this.ws = new WebSocket(this.url.replace("http", "ws"));
    var ws = this.ws;

    ws.onopen = this.onopen.bind(this);
    ws.onmessage = this.onmessage.bind(this);
    ws.onerror = this.onerror.bind(this);
    ws.onclose = this.onclose.bind(this);
};
_Connection.prototype.onopen=function(open) {
    console.log("onopen", this, arguments);
};
_Connection.prototype.onmessage=function(message) {
    //AppDispatcher.dispatchServerAction(...);
    console.log("onmessage", this, arguments);
};
_Connection.prototype.onerror=function(error) {
    console.log("onerror", this, arguments);
};
_Connection.prototype.onclose=function(close) {
    console.log("onclose", this, arguments);
};

var Connection = new _Connection(location.origin + "/updates");
