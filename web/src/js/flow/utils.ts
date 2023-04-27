import {Flow, HTTPMessage, HTTPRequest} from "../flow";

const defaultPorts = {
    "http": 80,
    "https": 443
};

export class MessageUtils {
    static getContentType(message: HTTPMessage): string | undefined {
        var ct = MessageUtils.get_first_header(message, /^Content-Type$/i);
        if (ct) {
            return ct.split(";")[0].trim();
        }
    }

    static get_first_header(
        message: HTTPMessage,
        regex: RegExp
    ): string | undefined {
        //FIXME: Cache Invalidation.
        // @ts-ignore
        const msg: HTTPMessage & { _headerLookups: { [regex: string]: string | undefined } } = message;
        if (!msg._headerLookups)
            Object.defineProperty(msg, "_headerLookups", {
                value: {},
                configurable: false,
                enumerable: false,
                writable: false
            });
        let regexStr = regex.toString();
        if (!(regexStr in msg._headerLookups)) {
            let header;
            for (let i = 0; i < msg.headers.length; i++) {
                if (!!msg.headers[i][0].match(regex)) {
                    header = msg.headers[i];
                    break;
                }
            }
            msg._headerLookups[regexStr] = header ? header[1] : undefined;
        }
        return msg._headerLookups[regexStr];
    }

    static match_header(message, regex) {
        var headers = message.headers;
        var i = headers.length;
        while (i--) {
            if (regex.test(headers[i].join(" "))) {
                return headers[i];
            }
        }
        return false;
    }

    static getContentURL(
        flow: Flow,
        part: HTTPMessage | "request" | "response" | "messages",
        view?: string,
        lines?: number
    ): string {
        if (flow.type === "http" && part === flow.request) {
            part = "request";
        } else if (flow.type === "http" && part === flow.response) {
            part = "response";
        }
        const lineStr = lines ? `?lines=${lines}` : "";
        return `./flows/${flow.id}/${part}/` + (view ? `content/${encodeURIComponent(view)}.json${lineStr}` : 'content.data');
    }
}

export class RequestUtils extends MessageUtils {
    static pretty_url(request: HTTPRequest): string {
        let port = "";
        if (defaultPorts[request.scheme] !== request.port) {
            port = ":" + request.port;
        }
        return request.scheme + "://" + request.pretty_host + port + request.path;
    }
}

export class ResponseUtils extends MessageUtils {

}

type ParsedUrl = {
    scheme?: string
    host?: string
    port?: number
    path?: string
}

var parseUrl_regex = /^(?:(https?):\/\/)?([^\/:]+)?(?::(\d+))?(\/.*)?$/i;
export var parseUrl = function (url): ParsedUrl | undefined {
    //there are many correct ways to parse a URL,
    //however, a mitmproxy user may also wish to generate a not-so-correct URL. ;-)
    var parts = parseUrl_regex.exec(url);
    if (!parts) {
        return undefined;
    }

    var scheme = parts[1],
        host = parts[2],
        port = parseInt(parts[3]),
        path = parts[4];
    if (scheme) {
        port = port || defaultPorts[scheme];
    }
    let ret: ParsedUrl = {};
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


const isValidHttpVersion_regex = /^HTTP\/\d+(\.\d+)*$/i;
export var isValidHttpVersion = function (httpVersion: string): boolean {
    return isValidHttpVersion_regex.test(httpVersion);
};


export function startTime(flow: Flow): number | undefined {
    switch (flow.type) {
        case "http":
            return flow.request.timestamp_start
        case "tcp":
            return flow.client_conn.timestamp_start
        case "dns":
            return flow.request.timestamp
    }
}

export function endTime(flow: Flow): number | undefined {
    switch (flow.type) {
        case "http":
            if (flow.websocket) {
                if (flow.websocket.timestamp_end)
                    return flow.websocket.timestamp_end
                if (flow.websocket.messages_meta.timestamp_last)
                    return flow.websocket.messages_meta.timestamp_last
            }
            if (flow.response) {
                return flow.response.timestamp_end
            }
            return undefined
        case "tcp":
            return flow.server_conn?.timestamp_end
        case "dns":
            return flow.response?.timestamp
    }

}

export const getTotalSize = (flow: Flow): number => {
    switch (flow.type) {
        case "http":
            let total = flow.request.contentLength || 0
            if (flow.response) {
                total += flow.response.contentLength || 0
            }
            if (flow.websocket) {
                total += flow.websocket.messages_meta.contentLength || 0
            }
            return total
        case "tcp":
            return flow.messages_meta.contentLength || 0
        case "dns":
            return flow.response?.size ?? 0
    }
}


export const canReplay = (flow: Flow): boolean => {
    return (flow.type === "http" && !flow.websocket)
}
