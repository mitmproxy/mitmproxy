/**
 * Flow subclass responsible for proper display of images
 */
define(["require",
        "lodash",
        "dojo/on",
        "dojo/query",
        "dojo/dom-construct",
        "dojo/Deferred",
        "../models/Flow",
        "../util/flowlist"],function(require,_,on,query,domConstruct,Deferred,Flow,flowlist){
	
	function preview(parentPreviewFunc){
		return function(){
			var deferred = new Deferred();
			var flow = this;
			
			require(["../traffic"],(function(traffic){
				flow.getSimilarFlows(3).then(function(ids){
					
					var flows = _.map(ids, function(i) {
						return traffic.get(i);
					});
					flows = _.filter(flows, function(f) {
						return (f.response.contentLength > 0);
					});
					
					var similarFlows = domConstruct.create("span");
					if(flows.length > 0){
						domConstruct.place("<h3>Similar Flows with Content:</h3>",similarFlows);
						domConstruct.place(flowlist(flows),similarFlows);
					} else {
						domConstruct.place("<p>No similar flows found.</p>",similarFlows);
					}
					
					parentPreviewFunc.apply(this,arguments).then(function(content){
						var span = domConstruct.create("span");
						domConstruct.place(content,span);
						domConstruct.place(similarFlows,span);
						deferred.resolve(span);
					});
				});
			}).bind(this));
			return deferred;
		};
	}	
	
	return Flow.extend({
		getPreview : preview(Flow.prototype.getPreview),
		getPreviewEmpty : preview(Flow.prototype.getPreviewEmpty)
	}, {
		matches : function(data) {
			if (data.responseCode)
				return (data.responseCode === 304);
			return false;
		},
		getCategory : function() {
			return "not-modified";
		}
	});
});