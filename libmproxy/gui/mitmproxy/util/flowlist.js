/**
 * Utility function that creats a flow list of the given flow ids
 */
define([
	"require",
	"dojo/dom-construct",
	"dojo/on",
	"lodash",
	"../MainLayout"
],function(require, domConstruct, on, _, MainLayout){
	
	return function(flows) {
		var ul = domConstruct.create("ul", {
			className: "flowlist"
		});

		_.each(flows, function(flow) {
			var li = domConstruct.create("li", {
				'className':'openDetail',
				'data-flow-id': flow.id
			}, ul);
			li.textContent = flow.request.fullPath + " - " + flow.response.contentLengthFormatted;
		});
		
		if(ul.children.length > 0){
			on(ul,"li:click",function(){
				MainLayout.mainContainer.selectedChildWidget.selectFlow(this.dataset.flowId);
			});
		}
		
		return ul;
	};

});