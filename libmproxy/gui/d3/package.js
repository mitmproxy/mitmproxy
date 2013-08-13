/*jshint unused:false */
var profile = (function() {
	var copyOnly = function(filename,mid){
		return (mid == "d3/d3.v3.min");
	};
	var amd = function(filename,mid){
		return (mid == "d3/main");
	};
	var miniExclude = function(f, m){
		return !(copyOnly(f,m) || amd(f,m) || (/\.css$/).test(m));
	};
	
	return {
		resourceTags: {
			amd: amd,
			copyOnly: copyOnly,
			miniExclude: miniExclude
		}			
	};
})();