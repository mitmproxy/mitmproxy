define(["dojo/_base/lang", "dojo/Deferred", "./MessageUtils"], function(lang, Deferred, MessageUtils) {
	"use strict";

	var defaultPorts = {
		"http": 80,
		"https": 443
	};

	var _parseParameter = function(pairStr) {
		var param = {};
		var pair = pairStr.split("=", 2);
		param.name = pair[0];
		param.value = (pair.length === 1) ? "" : pair[1];
		return param;
	};

	var RequestUtils = lang.mixin({}, MessageUtils);

	RequestUtils.getHostFormatted = function(request) {
		return request.host_guess ? request.host_guess : request.host;
	};
	RequestUtils.hasPayload = function(request) {
		return RequestUtils.hasContent(request) && (!RequestUtils.hasFormData(request));
	};
	RequestUtils.hasFormData = function(request) {
		var contentType = RequestUtils.getContentType(request);
		return (
			contentType &&
			RequestUtils.hasContent(request) &&
			contentType.match(/^application\/x-www-form-urlencoded\s*(;.*)?$/i));
	};
	RequestUtils.getFormData = function(request) {
		var def = new Deferred();
		RequestUtils.getContent(request).then(function(data) {
			data = data.split("&").map(_parseParameter);
			def.resolve(data);
		});
		return def;
	};
	RequestUtils.getFilename = function(request) {
		var path = request.path.split("?", 1)[0];
		var lastSlashIndex = path.lastIndexOf("/");
		var lastSegmentContainsDot = (path.indexOf(".", lastSlashIndex) >= 0);
		if (lastSegmentContainsDot) {
			return path.substr(lastSlashIndex + 1);
		} else {
			return path;
		}
	};
	RequestUtils.getQueryString = function(request) {
		var begin = request.path.indexOf("?");
		return begin >= 0 ? request.path.substr(begin) : "";
	};
	RequestUtils.getFullPath = function(request) {
		var fullpath = request.scheme + "://" + RequestUtils.getHostFormatted(request);
		if (!(request.scheme in defaultPorts) || defaultPorts[request.scheme] !== request.port)
			fullpath += ":" + request.port;
		fullpath += request.path.split("?", 1)[0];
		return fullpath;
	};



	//TODO: Add everything else

	return RequestUtils;
});