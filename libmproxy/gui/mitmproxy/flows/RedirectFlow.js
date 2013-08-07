/**
 * Flow subclass responsible for proper display of images
 */
define([
	"require",
	"dojo/_base/url",
	"dojo/Deferred",
	"dojo/dom-construct",
	"../models/Flow",
	"../util/flowlist"
],function(require, url, Deferred, domConstruct, Flow, flowlist){
	
	function preview(parentPreviewFunc){
		return function(){
			var deferred = new Deferred();
			var flow = this;
			
			var location = flow.response.getHeader(/^Location$/i);

			if(location) {
				location = new url(location);
				var path_with_query = location.path + (location.query ? "?"+location.query : "");
				//console.log(path_with_query);
				require(["../traffic"],(function(traffic){
					var flows = [];
					for(var i = flow.id + 1; i < Math.min(traffic.length,flow.id + 100); i++)  {
						var nextFlow = traffic.get(i);
						if ((flow.response.timestamp_end + 2) < nextFlow.request.timestamp_start)
							break;
						
						if(path_with_query === nextFlow.request.path 
              && (!location.host || location.host === nextFlow.request.hostFormatted || location.host === nextFlow.request.host))
							flows.push(nextFlow);
					}
					window.redirectFlows = flows;
					var nextFlows = domConstruct.create("span");
					if(flows.length > 0){
						domConstruct.place("<h3>Possible subsequent requests:</h3>",nextFlows);
						domConstruct.place(flowlist(flows),nextFlows);						
					} else {
						domConstruct.place("<p>No subsequent requests found.</p>",nextFlows);
					}
					
					parentPreviewFunc.apply(this,arguments).then(function(content){
						var container = domConstruct.create("div");
						domConstruct.place(content,container);
						domConstruct.place(nextFlows,container);
						deferred.resolve(container);
					});
					
				}).bind(this));
			} else {
				return parentPreviewFunc.apply(this,arguments);
			}
			return deferred;
		};
	}	
	
	return Flow.extend({
		getPreview : preview(Flow.prototype.getPreview),
		getPreviewEmpty : preview(Flow.prototype.getPreviewEmpty)
	}, {
		matches : function(data) {
			if (data.responseCode)
				return (301 <= data.responseCode && data.responseCode <= 303) || data.responseCode == 307;
			return false;
		},
		getCategory : function() {
			return "redirect";
		}
	});
});