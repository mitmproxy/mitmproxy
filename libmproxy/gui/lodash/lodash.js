define(["./_lodash"], function(_) {

	_.noConflict();
	
	_.extend = function(obj) {

		var extend = function(source) {
			for ( var prop in source) {
				var descriptor = Object.getOwnPropertyDescriptor(source, prop);
				if (descriptor === undefined) {
					var proto = Object.getPrototypeOf(source);
					while (descriptor === undefined) {
						descriptor = Object.getOwnPropertyDescriptor(proto, prop);
						proto = Object.getPrototypeOf(proto);
					}
				}
				Object.defineProperty(obj, prop, descriptor);
			}
		};
		
		_.each(Array.prototype.slice.call(arguments, 1), extend);
		return obj;
	};
	return _;
});
