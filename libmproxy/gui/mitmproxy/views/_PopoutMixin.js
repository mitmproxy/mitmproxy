define(["dojo/_base/declare",
		"lodash",
		"dojo/query", 
		"dojo/text!./templates/_PopoutMixin.html",
		"dojo/NodeList-traverse"
], function(declare, _, query, templateString) {

	var template = _.template(templateString);

	return declare([], {
		popOut: function(event) {

			console.log(this, arguments);

			var nav = query(event.target).parents("ul");
			nav.addClass("hide");
			var content = this.domNode.innerHTML;
			nav.removeClass("hide");

			var html = template({
				"title": this.title + " - HoneyProxy" || "HoneyProxy",
				"content": content
			});
			var win = window.open("", _.uniqueId("popout"), "height=400,width=500");
			win.document.write(html);
			win.document.close();


		}
	});
});