/*jshint unused:false */
var dojoConfig = {
	async: true,
	basePath: ".",
	baseUrl: ".",

	packages: [
		'mitmproxy', 
		'bootstrap', 
		'jquery', 
		'font-awesome',
		'highlight', 
		'lodash', 
		'codemirror', 
		'd3', 
		'dojo', 
		'dijit', 
		'dojox', 
		'dgrid', 
		'xstyle', 
		'put-selector',
		'legacy',
		{
			name: "ReportScripts",
			location: "/api/fs"
		} ]
};