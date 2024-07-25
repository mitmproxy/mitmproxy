import { Flow, HTTPHeader, HTTPMessage, HTTPRequest } from "../flow";

const defaultPorts = {
    http: 80,
    https: 443,
};

export class MessageUtils {
    static getContentType(message: HTTPMessage): string | undefined {
        const ct = MessageUtils.get_first_header(message, /^Content-Type$/i);
        if (ct) {
            return ct.split(";")[0].trim();
        }
    }

    static get_first_header(
        message: HTTPMessage,
        regex: RegExp,
    ): string | undefined {
        //FIXME: Cache Invalidation.
        // @ts-expect-error hidden cache on object
        const msg: HTTPMessage & {
            _headerLookups: { [regex: string]: string | undefined };
        } = message;
        if (!msg._headerLookups)
            Object.defineProperty(msg, "_headerLookups", {
                value: {},
                configurable: false,
                enumerable: false,
                writable: false,
            });
        const regexStr = regex.toString();
        if (!(regexStr in msg._headerLookups)) {
            let header: HTTPHeader | undefined = undefined;
            for (let i = 0; i < msg.headers.length; i++) {
                if (msg.headers[i][0].match(regex)) {
                    header = msg.headers[i];
                    break;
                }
            }
            msg._headerLookups[regexStr] = header ? header[1] : undefined;
        }
        return msg._headerLookups[regexStr];
    }

    static match_header(message, regex) {
        const headers = message.headers;
        let i = headers.length;
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
        lines?: number,
    ): string {
        if (flow.type === "http" && part === flow.request) {
            part = "request";
        } else if (flow.type === "http" && part === flow.response) {
            part = "response";
        }
        const lineStr = lines ? `?lines=${lines}` : "";
        return (
            `./flows/${flow.id}/${part}/` +
            (view
                ? `content/${encodeURIComponent(view)}.json${lineStr}`
                : "content.data")
        );
    }
}

export class RequestUtils extends MessageUtils {
    static pretty_url(request: HTTPRequest): string {
        let port = "";
        if (defaultPorts[request.scheme] !== request.port) {
            port = ":" + request.port;
        }
        return (
            request.scheme + "://" + request.pretty_host + port + request.path
        );
    }
}

export class ResponseUtils extends MessageUtils {}

type ParsedUrl = {
    scheme?: string;
    host?: string;
    port?: number;
    path?: string;
};

const parseUrl_regex = /^(?:(https?):\/\/)?([^/:]+)?(?::(\d+))?(\/.*)?$/i;
export const parseUrl = function (url): ParsedUrl | undefined {
    //there are many correct ways to parse a URL,
    //however, a mitmproxy user may also wish to generate a not-so-correct URL. ;-)
    const parts = parseUrl_regex.exec(url);
    if (!parts) {
        return undefined;
    }

    const scheme = parts[1];
    const host = parts[2];
    const optionalPort = parseInt(parts[3]);
    const path = parts[4];
    const port = scheme ? optionalPort || defaultPorts[scheme] : optionalPort;
    const ret: ParsedUrl = {};
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
export const isValidHttpVersion = function (httpVersion: string): boolean {
    return isValidHttpVersion_regex.test(httpVersion);
};

export function startTime(flow: Flow): number | undefined {
    switch (flow.type) {
        case "http":
            return flow.request.timestamp_start;
        case "tcp":
        case "udp":
            return flow.client_conn.timestamp_start;
        case "dns":
            return flow.request.timestamp;
    }
}

export function endTime(flow: Flow): number | undefined {
    switch (flow.type) {
        case "http":
            if (flow.websocket) {
                if (flow.websocket.timestamp_end)
                    return flow.websocket.timestamp_end;
                if (flow.websocket.messages_meta.timestamp_last)
                    return flow.websocket.messages_meta.timestamp_last;
            }
            if (flow.response) {
                return flow.response.timestamp_end;
            }
            return undefined;
        case "tcp":
            return flow.server_conn?.timestamp_end;
        case "udp":
            // there is no formal close here and server_conn.timestamp_end usually represents the timeout timestamp,
            // which is not quite what we want.
            return flow.messages_meta.timestamp_last;
        case "dns":
            return flow.response?.timestamp;
    }
}

export const getTotalSize = (flow: Flow): number => {
    switch (flow.type) {
        case "http": {
            let total = flow.request.contentLength || 0;
            if (flow.response) {
                total += flow.response.contentLength || 0;
            }
            if (flow.websocket) {
                total += flow.websocket.messages_meta.contentLength || 0;
            }
            return total;
        }
        case "tcp":
        case "udp":
            return flow.messages_meta.contentLength || 0;
        case "dns":
            return flow.response?.size ?? 0;
    }
};

export const canReplay = (flow: Flow): boolean => {
    return flow.type === "http" && !flow.websocket;
};

export const getIcon = (flow: Flow): string => {
    if (flow.type !== "http") {
        if (flow.client_conn.tls_version === "QUIC") {
            return `resource-icon-quic`;
        }
        return `resource-icon-${flow.type}`;
    }
    if (flow.websocket) {
        return "resource-icon-websocket";
    }
    if (!flow.response) {
        return "resource-icon-plain";
    }

    const contentType = ResponseUtils.getContentType(flow.response) || "";

    if (flow.response.status_code === 304) {
        return "resource-icon-not-modified";
    }
    if (300 <= flow.response.status_code && flow.response.status_code < 400) {
        return "resource-icon-redirect";
    }
    if (contentType.indexOf("image") >= 0) {
        return "resource-icon-image";
    }
    if (contentType.indexOf("javascript") >= 0) {
        return "resource-icon-js";
    }
    if (contentType.indexOf("css") >= 0) {
        return "resource-icon-css";
    }
    if (contentType.indexOf("html") >= 0) {
        return "resource-icon-document";
    }

    return "resource-icon-plain";
};

export const mainPath = (flow: Flow): string => {
    switch (flow.type) {
        case "http":
            return RequestUtils.pretty_url(flow.request);
        case "tcp":
        case "udp":
            return `${flow.client_conn.peername.join(
                ":",
            )} ↔ ${flow.server_conn?.address?.join(":")}`;
        case "dns":
            return `${flow.request.questions
                .map((q) => `${q.name} ${q.type}`)
                .join(", ")} = ${
                (flow.response?.answers.map((q) => q.data).join(", ") ??
                    "...") ||
                "?"
            }`;
    }
};

export const statusCode = (flow: Flow): string | number | undefined => {
    switch (flow.type) {
        case "http":
            return flow.response?.status_code;
        case "dns":
            return flow.response?.response_code;
        default:
            return undefined;
    }
};

export const getMethod = (flow: Flow): string => {
    switch (flow.type) {
        case "http":
            return flow.websocket
                ? flow.client_conn.tls_established
                    ? "WSS"
                    : "WS"
                : flow.request.method;
        case "dns":
            return flow.request.op_code;
        default:
            return flow.type.toUpperCase();
    }
};

export const getVersion = (flow: Flow): string => {
    switch (flow.type) {
        case "http":
            return flow.request.http_version;
        default:
            return "";
    }
};

export const sortFunctions = {
    tls: (flow: Flow) => flow.type === "http" && flow.request.scheme,
    icon: getIcon,
    index: () => 0, // this is broken right now - ideally we switch to uuid7s on the backend and use that.
    path: mainPath,
    method: getMethod,
    version: getVersion,
    status: statusCode,
    size: getTotalSize,
    time: (flow: Flow) => {
        const start = startTime(flow);
        const end = endTime(flow);
        return start && end && end - start;
    },
    timestamp: startTime,
    quickactions: () => 0,
    comment: (flow: Flow) => flow.comment,
};
