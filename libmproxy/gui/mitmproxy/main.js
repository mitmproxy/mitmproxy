if (define && define.amd) //for the builder
	define.amd.jQuery = true;
require(
["dojo/when",
		"dojo/on",
		"dojo/topic",
		"HoneyProxy/MainLayout",
		"HoneyProxy/websocket",
		"HoneyProxy/flow/FlowFactory",
		"HoneyProxy/traffic",
		"HoneyProxy/util/versionCheck",
		"HoneyProxy/util/sampleFlow",
		"HoneyProxy/util/requestAuthenticator",
		"HoneyProxy/search"
], function(when, on, topic, MainLayout, websocket, FlowFactory, flowStore, versionCheck, sampleFlow) {

	//Debug
	window.HoneyProxy = {
		flowStore: flowStore,
		sampleFlow: sampleFlow,
		MainLayout: MainLayout
	};

	topic.subscribe("HoneyProxy/newFlow", function(flow) {
		FlowFactory.makeFlow(flow);
		flowStore.notify(flow);
	});

	window.setTimeout(versionCheck, 3000);
});