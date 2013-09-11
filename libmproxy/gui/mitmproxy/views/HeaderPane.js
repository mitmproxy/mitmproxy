define([
        "require", 
        "dojo/_base/declare", 
        "../util/_ReactiveTemplatedWidget",
        "../MainLayout",
        "jquery",
        "../util/smart-popover",
        "dojo/text!./templates/HeaderPane.html",
        "dojo/text!./templates/HeaderPane-MainMenu.html"],
function(require, declare, _ReactiveTemplatedWidget, MainLayout, $, _, template, template_menu) {

	return declare([ _ReactiveTemplatedWidget ], {
		templateString: template,
        postCreate: function(){
            $(this.brandNode).smartPopover({
                placement: "bottom",
                html: true,
                title: "mitmproxy",
                content: template_menu,
                container: "body"
            });
        },
        destroy: function(){
            $(this.brandNode).popover("destroy");
        },
		showPane: function(id){
			MainLayout.showPane(id);
		}
	});
	
});