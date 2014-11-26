function Connection(url) {
    if(url[0] != "/"){
        this.url = url;
    } else {
        this.url = location.origin.replace("http", "ws") + url;
    }
    var ws = new WebSocket(this.url);
    ws.onopen = function(){
        this.onopen.apply(this, arguments);
    }.bind(this);
    ws.onmessage = function(){
        this.onmessage.apply(this, arguments);
    }.bind(this);
    ws.onerror = function(){
        this.onerror.apply(this, arguments);
    }.bind(this);
    ws.onclose = function(){
        this.onclose.apply(this, arguments);
    }.bind(this);
    this.ws = ws;
}
Connection.prototype.onopen = function (open) {
    console.debug("onopen", this, arguments);
};
Connection.prototype.onmessage = function (message) {
    console.warn("onmessage (not implemented)", this, message.data);
};
Connection.prototype.onerror = function (error) {
    EventLogActions.add_event("WebSocket Connection Error.");
    console.debug("onerror", this, arguments);
};
Connection.prototype.onclose = function (close) {
    EventLogActions.add_event("WebSocket Connection closed.");
    console.debug("onclose", this, arguments);
};
Connection.prototype.close = function(){
    this.ws.close();
};