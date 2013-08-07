/*
 * A sample flow - used for autocompletion in the reporteditor
 */
define(
["../flow/FlowFactory"], function(FlowFactory) {
	var flow = {
		"id": 1,
		"version": [0, 9],
		"view": true, //TODO
		"request": {
			"contentChecksums": {},
			"headers": [
				["Host", "example.com"]
			],
			"timestamp_start": 1234567890.123,
			"timestamp_end": 1234567890.123,
			"contentLength": 0,
			"method": "GET",
			"client_conn": {
				"error": null,
				"requestcount": 1,
				"address": ["127.0.0.1", 64000]
			},
			"host": "example.com",
			"path": "/foo",
			"scheme": "http",
			"port": 80,
			"httpversion": [1, 1]
		},
		"response": {
			"headers": [
				["Content-Length", "42"]
			],
			"cert": null,
			"code": 200,
			"contentChecksums": {
				"Checksum": {
					"sha256": "sha2563fac9fbad9adf6db2a3f508f60c5a92e7d1d3b011a29222da2ee95caaa",
					"md5": "md55abdbf686beaccbf3c12180549aaa"
				}
			},
			"msg": "OK",
			"timestamp_start": 1234567890.123,
			"timestamp_end": 1234567890.123,
			"contentLength": 42,
			"httpversion": [1, 1]
		},
		"error": null
	};
	FlowFactory.makeFlow(flow);
	return flow;
});