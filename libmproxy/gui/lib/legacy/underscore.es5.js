(function() {
	var nativeGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
	var nativeDefineProperty = Object.defineProperty;
	var nativeGetPrototypeOf = Object.getPrototypeOf;
	var slice = Array.prototype.slice;
	var nativePropertyAccessWorksForObjects;
	
	try {
		nativeGetOwnPropertyDescriptor({"a" : true}, "a");
		nativePropertyAccessWorksForObjects = true;
	} catch (e) {
		nativePropertyAccessWorksForObjects = false;
	}

	_.extend = function(obj) {

		var nativeExtend = function(source) {
			for ( var prop in source) {
				var descriptor = nativeGetOwnPropertyDescriptor(source, prop);
				if(descriptor === undefined){
					var proto = nativeGetPrototypeOf(source);
					while(descriptor === undefined) {
						descriptor = nativeGetOwnPropertyDescriptor(proto, prop);
						proto = nativeGetPrototypeOf(proto);
					}
				}
				nativeDefineProperty(obj, prop, descriptor);
			}
		};
		var simpleExtend = function(source) {
			for ( var prop in source) {
				obj[prop] = source[prop];
			}
		};

		_.each(slice.call(arguments, 1),
			(nativeGetOwnPropertyDescriptor && nativeDefineProperty && nativePropertyAccessWorksForObjects)
			? nativeExtend : simpleExtend);
		return obj;
	};
})();