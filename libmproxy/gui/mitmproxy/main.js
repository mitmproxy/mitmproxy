if (define && define.amd) //for the builder
	define.amd.jQuery = true;
require(
["dojo/when",
		"dojo/on",
		"dojo/topic",
		"mitmproxy/MainLayout",
		"mitmproxy/flow/FlowFactory",
		"mitmproxy/traffic",
		"mitmproxy/util/versionCheck",
		"mitmproxy/util/sampleFlow",
		"mitmproxy/util/requestAuthenticator",
		"mitmproxy/search"
], function(when, on, topic, MainLayout, FlowFactory, flowStore, versionCheck, sampleFlow) {

	//Debug
	window.mitmproxy = {
		flowStore: flowStore,
		sampleFlow: sampleFlow,
		MainLayout: MainLayout
	};

	topic.subscribe("mitmproxy/newFlow", function(flow) {
		FlowFactory.makeFlow(flow);
		flowStore.notify(flow);
	});

    /* Super Ugly Workaround to refresh the grid
    manually as long as the mitmproxy isn't finished yet */
    window.setInterval(function(){
        var grid = mitmproxy.MainLayout.trafficPane.grid;
        if(grid._total == 0){
           grid.refresh();
        } else {
            flowStore.notify();
        }
    },1000);

	window.setTimeout(versionCheck, 3000);
});