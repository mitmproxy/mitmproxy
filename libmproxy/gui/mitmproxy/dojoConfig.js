/*jshint unused:false */
var dojoConfig = {
	async: true,
	basePath: "..",
	baseUrl: ".",
	
	packages: [ {
		name: "HoneyProxy",
		location: "./HoneyProxy"
	}, {
		name: "ReportScripts",
		location: "/api/fs/report_scripts"
	}, {
		name: "jquery",
		main: "jquery.min",
		location: "./lib/jquery",
		destLocation:"./lib/jquery"
	}, {
		name: "highlight",
		main: "highlight",
		location: "./lib/highlight",
		destLocation:"./lib/highlight"
	}, {
		name: "lodash",
		main: "lodash",
		location: "./lib/lodash",
		destLocation:"./lib/lodash"
	}, {
		name: "codemirror",
		location: "./lib/codemirror",
		destLocation:"./lib/codemirror"
	}, {
		name: "d3",
		location: "./lib/d3",
		destLocation:"./lib/d3"
	}, {
    name: "dojo",
    location: "./lib/dojo",
    destLocation:"./lib/dojo"
	}, {
    name: "dijit",
    location: "./lib/dijit",
    destLocation:"./lib/dijit"
	}, {
    name: "dojox",
    location: "./lib/dojox",
    destLocation:"./lib/dojox"
	}, {
	name: "dgrid",
    location: "./lib/dgrid",
    destLocation:"./lib/dgrid"
	}, {
    name: "xstyle",
    location: "./lib/xstyle",
    destLocation:"./lib/xstyle"
	}, {
    name: "put-selector",
    location: "./lib/put-selector",
    destLocation:"./lib/put-selector"
	}, {
    name: "bootstrap",
    location: "./lib/bootstrap",
    destLocation:"./lib/bootstrap"
	}, {
    name: "legacy",
    location: "./lib/legacy",
    destLocation:"./lib/legacy"
	}
	]
};