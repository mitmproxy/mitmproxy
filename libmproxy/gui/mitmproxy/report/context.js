define(["lodash",
		"jquery",
		"dojo/_base/declare",
		"dojo/_base/lang",
		"dojo/dom-construct",
		"dojo/Deferred",
		"dojo/on",
		"../traffic",
		"../flow/MessageUtils",
		"../flow/RequestUtils",
		"../flow/ResponseUtils",
		"../util/sampleFlow"
], function(_, $, declare, lang, domConstruct, Deferred, on, traffic, MessageUtils, RequestUtils, ResponseUtils, sampleFlow) {
	return {
		"flow": {
			"request": sampleFlow.request,
			"response": sampleFlow.response,
			"id": sampleFlow.id,
			"getSimilarFlows": sampleFlow.getSimilarFlows
		},
		"detailView": {
			showDetails: function() {}
		},
		"out": document.createElement("div"),
		"MessageUtils": MessageUtils,
		"RequestUtils": RequestUtils,
		"ResponseUtils": ResponseUtils,
		"traffic": traffic,
		"_": _,
		"$": $,
		"domConstruct": domConstruct,
		"Deferred": Deferred,
		"on": on,
		"declare": declare,
		"lang": lang
	};
});