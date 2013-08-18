define(["./flow/FlowStore"],function(FlowStore){
	
	var flowStore = new FlowStore({
		target: "/api/flows"
	});

	return flowStore;
});