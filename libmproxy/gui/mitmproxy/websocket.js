define([ "./config", "dojo/json", "dojo/topic", "dojo/Deferred" ], function(
	config, JSON, topic, Deferred) {
	
	/**
	 * HoneyProxy Websocket Client. Connect to the WS URL, perform authentication
	 * and listen for new flows or responses to sync requests.
	 */
	var websocket = {
		send: function(jsonMsg) {
			this.ws.send(JSON.stringify(jsonMsg));
		},
		onmessage: function onmessage(o) {
			var e = JSON.parse(o.data);
			switch (e.msg) {
			case "Authenticated.":
				websocket.authenticated.resolve("authenticated");
				console.debug("WebSocket connection authenticated.");
				break;
			case "read":
				console.error("FIXME: legacy code");
				/* 
				if (e.id in Backbone._syncrequests) {
					var req = Backbone._syncrequests[e.id];
					window.clearTimeout(req.onError);
					req.success(e.data);
				} */
				break;
			case "newflow":
				topic.publish("HoneyProxy/newFlow", e.data);
				break;
			default:
				console.warn("unsupported message", e);
				break;
			}
			
		},
		authenticated: new Deferred(),
		init: function() {
			var wsUrl = "ws://" + window.location.hostname + ":" + config.get("ws-port");
			this.ws = new WebSocket(wsUrl);
			this.ws.onopen = (function() {
				this.send({
					action: "auth",
					key: config.get("auth")
				});
				console.debug("WebSocket connection established.");
			}).bind(this);
			websocket.ws.onmessage = this.onmessage.bind(this);
		}
	};
	
	websocket.init();
	
	/**
	 * Backbone.sync implementation using WebSockets. Supplies an id for each
	 * request and waits for a response with this id. TODO: Use the JSON API
	 * instead. WebSocket should be used for communicating newly arrived flows,
	 * but it's clearly not made for a 1:1 request/response model.
	 */
	 /*
	Backbone._syncrequests = {};
	Backbone.sync = function(method, model, options) {
		if (method != "read") {
			console.warn("only read is supported");
			return;
		}
		
		var id = model.id ? model.id : "all";
		var msg = {
			action: "read",
			id: id
		};
		Backbone._syncrequests[id] = {
			onError: window.setTimeout(function() {
				options.error("WebSocket Timeout.");
			}, 5000),
			success: options.success
		};
		websocket.send(msg);
		
	};
	*/
	
	return websocket;
});
