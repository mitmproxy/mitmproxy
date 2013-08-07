define([
		"exports",
		"dojo/query",
		"dijit/layout/BorderContainer",
		"dijit/layout/TabContainer",
		"dijit/layout/StackContainer",
		"dijit/layout/ContentPane",
		"./views/HeaderPane",
		"./views/TrafficPane",
		"./views/ReportPane",
		"./traffic",
		"./config",
		"dojo/domReady!"
], function(exports, query, BorderContainer, TabContainer, StackContainer, ContentPane, HeaderPane, TrafficPane, ReportPane, traffic, config) {

	//appLayout covers everything
	var appLayout = new BorderContainer({
		design: "headline",
		liveSplitters: false,
		gutters: false
	}, "appLayout");

	var header = new HeaderPane({
		region: "top",
		id: "header",
		style: "width: 100%;"
	});


	//main covers the whole content area, but not the header
	var main = new StackContainer({
		id: "main",
		region: "center"
	});

	//populate appLayout
	appLayout.addChild(header);
	appLayout.addChild(main);


	//Traffic Pane, our default view with search sidebar and traffic table.
	var trafficPane = new TrafficPane({
		liveSplitters: false,
		gutters: false
	});

	//Report Pane
	var reportPane = new ReportPane({
		liveSplitters: false,
		gutters: false
	});

	//populate main
	main.addChild(trafficPane);
	main.addChild(reportPane);

	appLayout.startup();

	//TODO: When refactoring, replace with code that doesn't depend on domReady
	//TODO: When refactoring, remove all references to specific Views and make views lazy-load
	/*
	var fixme = traffic.query();
	fixme.on = function(type, callback, context) {
		switch (type) {
			case "add":
				return fixme.observe(function(object, removedFrom, insertedInto) {
					if (insertedInto !== -1)
						callback.call(context, object, fixme, {
							index: insertedInto
						});
				});
			case "remove":
				return fixme.observe(function(object, removedFrom, insertedInto) {
					if (removedFrom !== -1)
						callback.call(context, object);
				});
			case "reset":
				break;
			default:
				throw "unimplemented";
		}
		return fixme.observe();
	};*/
	/*
	var trafficView = new TrafficView({
		collection: fixme,
		el: $("#trafficTable .data tbody")[0]
	});

	trafficView.$el.on("click", "tr", function() {
		trafficPane.selectFlow($(this).data("flow-id"));
	});
	exports.trafficView = trafficView;
	*/
	exports.mainContainer = main;
	exports.showPane = function(index) {
		main.selectChild(main.getChildren()[index]);
	};
	exports.header = header;

	exports.trafficPane = trafficPane;

	return exports;
});