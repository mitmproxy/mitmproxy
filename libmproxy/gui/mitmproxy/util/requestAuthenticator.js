/**
 * All HoneyProxy API calls that have side effects (e.g. writing data to disk)
 * need to pass the valid auth token to prevent CSRF attacks.
 * This token can be obtained by calling /api/authtoken
 * 
 * If you are calling sensitive functions, 
 * make sure that the promise returned by this module has been fulfilled.
 * 
 * To make this clear:
 * HoneyProxy has NO built-in protection against MITM attacks.
 * Run it on localhost for sensitive operations or tunnel appropriately.
 */
define(["exports", "dojo/request", "dojo/request/notify", "dojo/Deferred"],function(exports, request, notify, Deferred){
	
	var def = new Deferred();
	
	request("/api/token",{handleAs:"json"}).then(function(data){
		var token = data.token;
		notify("send", function(req){
			if(req.options.method !== "GET") {
				req.xhr.setRequestHeader("X-Request-Token",token);
			}
		});
		def.resolve(token === null ? false : true);
	},function(){
		def.reject(arguments);
	});
	
	exports.active = def;
	return exports;
});