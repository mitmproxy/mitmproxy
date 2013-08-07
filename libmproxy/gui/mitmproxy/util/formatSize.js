define([],function(){
	
	return function(size){
		
		var prefix = ["B","KB","MB","GB","TB"];
		while(size > 1024 && prefix.length > 1){
			prefix.shift();
			size = size / 1024;
		}
		return (Math.floor(size*100)/100.0)+prefix.shift();
	};
});