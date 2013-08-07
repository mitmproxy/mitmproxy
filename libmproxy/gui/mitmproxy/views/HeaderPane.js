define([
        "require", 
        "dojo/_base/declare", 
        "../util/_ReactiveTemplatedWidget",
        "../MainLayout",
        "../config",
        "dojo/text!./templates/HeaderPane.html" ], 
function(require, declare, _ReactiveTemplatedWidget, MainLayout, config, template) {

	return declare([ _ReactiveTemplatedWidget ], {
		templateString: template,
		showPane: function(id){
			MainLayout.showPane(id);
		}
	});
	
});