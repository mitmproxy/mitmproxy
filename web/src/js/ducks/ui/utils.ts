import { Flow } from "../../flow";

/**
 * mitmwebnext implementation.
 */
export function tabsForFlowNext(flow: Flow): {
    request: string[];
    response: string[];
} {
    let responseTabs: string[] = [],
        requestTabs: string[] = [];

    switch (flow.type) {
        case "http":
            responseTabs = [
                "headers",
                ...filterExistingProperties(flow, ["response", "websocket"]),
            ];
            requestTabs = ["headers", "query", "cookies", "body"];
            break;
        case "tcp":
            responseTabs = ["tcpmessages"];
            break;
        case "udp":
            responseTabs = ["udpmessages"];
            break;
        case "dns":
            responseTabs = filterExistingProperties(flow, [
                "request",
                "response",
            ]).map((s) => "dns" + s);
            break;
    }

    if (flow.error) {
        responseTabs.push("error");
    }

    responseTabs.push("connection");
    responseTabs.push("timing");
    responseTabs.push("comment");

    return { response: responseTabs, request: requestTabs };
}

/**
 * mitmweb implementation.
 */
export function tabsForFlow(flow: Flow): string[] {
    let tabs;
    switch (flow.type) {
        case "http":
            tabs = ["request", "response", "websocket"].filter((k) => flow[k]);
            break;
        case "tcp":
            tabs = ["tcpmessages"];
            break;
        case "udp":
            tabs = ["udpmessages"];
            break;
        case "dns":
            tabs = ["request", "response"]
                .filter((k) => flow[k])
                .map((s) => "dns" + s);
            break;
    }

    if (flow.error) tabs.push("error");
    tabs.push("connection");
    tabs.push("timing");
    tabs.push("comment");
    return tabs;
}

/**
 * The flow may not yet contain all properties if it hasn't been finalized yet.
 * This function filters them out.
 */
function filterExistingProperties(flow: Flow, tabs: string[]) {
    return tabs.filter((tab) => {
        return (flow as any)[tab] !== undefined;
    });
}
