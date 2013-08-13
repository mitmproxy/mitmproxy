if (define && define.amd) //for the builder
	define.amd.jQuery = true;
require(
["dojo/when",
		"dojo/on",
		"dojo/topic",
		"mitmproxy/MainLayout",
		"mitmproxy/websocket",
		"mitmproxy/flow/FlowFactory",
		"mitmproxy/traffic",
		"mitmproxy/util/versionCheck",
		"mitmproxy/util/sampleFlow",
		"mitmproxy/util/requestAuthenticator",
		"mitmproxy/search"
], function(when, on, topic, MainLayout, websocket, FlowFactory, flowStore, versionCheck, sampleFlow) {

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

	window.setTimeout(versionCheck, 3000);
});