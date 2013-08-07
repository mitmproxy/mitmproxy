/**
 * basic config for our gui.
 */
define(["dojo/json","dojo/text!/api/config"], function(JSON,configstr){
	
	var Config = function(data){
		this.storage = data || {};
	};
	Config.prototype.get = function(id){
		return this.storage[id];
	};
	Config.prototype.set = function(id,val){
		this.storage[id] = val;
	};
	
	var config = new Config(JSON.parse(configstr));
	
	return config;
});