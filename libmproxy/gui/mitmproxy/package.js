/*jshint unused:false */
var profile = (function() {
	
	var copyOnlyFiles = {"package.js": true, "package.json" : true};
	
	var ignore = function(filename,mid){
		return (/\.less$/).test(filename);
	};
	
	var copyOnly = function(filename){
		return (filename in copyOnlyFiles);
	};
	
	var amd = function(filename, mid) {
		//console.log("Filename: " + filename, "Mid: " + mid);
		if(copyOnly(filename))
			return false;
		return (/\.js$/).test(filename);
		
	};
	
	return {
		resourceTags: {
			test: function() {
				return false;
			},
			
			copyOnly: copyOnly,
			amd: amd,
			ignore: ignore
		}		
		
		//trees: [ [ ".", ".", /(\/\.)|(~$)/ ] ]
	};
})();