var _ = require("lodash");
var $ = require("jquery");

var defaultPorts = {
    "http": 80,
    "https": 443
};

var MessageUtils = {
    getContentType: function (message) {
        var ct = this.get_first_header(message, /^Content-Type$/i);
        if(ct){
            return ct.split(";")[0].trim();
        }
    },
    get_first_header: function (message, regex) {
        //FIXME: Cache Invalidation.
        if (!message._headerLookups)
            Object.defineProperty(message, "_headerLookups", {
                value: {},
                configurable: false,
                enumerable: false,
                writable: false
            });
        if (!(regex in message._headerLookups)) {
            var header;
            for (var i = 0; i < message.headers.length; i++) {
                if (!!message.headers[i][0].match(regex)) {
                    header = message.headers[i];
                    break;
                }
            }
            message._headerLookups[regex] = header ? header[1] : undefined;
        }
        return message._headerLookups[regex];
    },
    match_header: function (message, regex) {
        var headers = message.headers;
        var i = headers.length;
        while (i--) {
            if (regex.test(headers[i].join(" "))) {
                return headers[i];
            }
        }
        return false;
    },
    getContentURL: function (flow, message, viewType) {
        if (message === flow.request) {
            message = "request";
        } else if (message === flow.response) {
            message = "response";
        }

        if (viewType !== undefined)
            return "/flows/" + flow.id + "/" + message + "/content/" + viewType;
        else
            return "/flows/" + flow.id + "/" + message + "/content";
    },
    getContent: function (flow, message, viewType) {
        var url;
        if (viewType !== undefined)
            url = MessageUtils.getContentURL(flow, message, viewType);
        else
            url = MessageUtils.getContentURL(flow, message);
        return $.get(url);
    }
};

var RequestUtils = _.extend(MessageUtils, {
    pretty_host: function (request) {
        //FIXME: Add hostheader
        return request.host;
    },
    pretty_url: function (request) {
        var port = "";
        if (defaultPorts[request.scheme] !== request.port) {
            port = ":" + request.port;
        }
        return request.scheme + "://" + this.pretty_host(request) + port + request.path;
    }
});

var ResponseUtils = _.extend(MessageUtils, {});


var parseUrl_regex = /^(?:(https?):\/\/)?([^\/:]+)?(?::(\d+))?(\/.*)?$/i;
var parseUrl = function (url) {
    //there are many correct ways to parse a URL,
    //however, a mitmproxy user may also wish to generate a not-so-correct URL. ;-)
    var parts = parseUrl_regex.exec(url);
    if(!parts){
        return false;
    }

    var scheme = parts[1],
        host = parts[2],
        port = parseInt(parts[3]),
        path = parts[4];
    if (scheme) {
        port = port || defaultPorts[scheme];
    }
    var ret = {};
    if (scheme) {
        ret.scheme = scheme;
    }
    if (host) {
        ret.host = host;
    }
    if (port) {
        ret.port = port;
    }
    if (path) {
        ret.path = path;
    }
    return ret;
};


var isValidHttpVersion_regex = /^HTTP\/\d+(\.\d+)*$/i;
var isValidHttpVersion = function (httpVersion) {
    return isValidHttpVersion_regex.test(httpVersion);
};

var parseHttpVersion = function (httpVersion) {
    httpVersion = httpVersion.replace("HTTP/", "").split(".");
    return _.map(httpVersion, function (x) {
        return parseInt(x);
    });
};

module.exports = {
    ResponseUtils: ResponseUtils,
    RequestUtils: RequestUtils,
    MessageUtils: MessageUtils,
    parseUrl: parseUrl,
    parseHttpVersion: parseHttpVersion,
    isValidHttpVersion: isValidHttpVersion
};