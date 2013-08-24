define(["dojo/_base/declare", "../../util/_ReactiveTemplatedWidget", "../_PopoutMixin","../../flow/FlowBindings", "../../flow/MessageUtils", "../../flow/RequestUtils", "../../flow/ResponseUtils"], 
	function(declare, _ReactiveTemplatedWidget, _PopoutMixin, flowBindings, MessageUtils, RequestUtils, ResponseUtils) {

	return declare([_ReactiveTemplatedWidget, _PopoutMixin], {
		context: {
			MessageUtils: MessageUtils,
			RequestUtils: RequestUtils,
			ResponseUtils: ResponseUtils
		},
		bindings: flowBindings
	});

});