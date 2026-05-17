import * as React from "react";
import type { FunctionComponent } from "react";
import { Request, Response } from "./FlowView/HttpMessages";
import {
    Request as DnsRequest,
    Response as DnsResponse,
} from "./FlowView/DnsMessages";
import Connection from "./FlowView/Connection";
import Error from "./FlowView/Error";
import Timing from "./FlowView/Timing";
import WebSocket from "./FlowView/WebSocket";
import Comment from "./FlowView/Comment";
import { selectTab } from "../ducks/ui/flow";
import { useAppDispatch, useAppSelector } from "../ducks";
import type { DNSFlow, Error as FlowError, Flow, HTTPFlow } from "../flow";
import classnames from "classnames";
import TcpMessages from "./FlowView/TcpMessages";
import UdpMessages from "./FlowView/UdpMessages";
import * as flowsActions from "../ducks/flows";

type TabId =
    | "request"
    | "response"
    | "error"
    | "connection"
    | "timing"
    | "websocket"
    | "tcpmessages"
    | "udpmessages"
    | "dnsrequest"
    | "dnsresponse"
    | "comment";

type TabProps = {
    flow: Flow;
};

function hasError(flow: Flow): flow is Flow & { error: FlowError } {
    return !!flow.error;
}

function hasWebSocket(
    flow: Flow,
): flow is HTTPFlow & Required<Pick<HTTPFlow, "websocket">> {
    return flow.type === "http" && !!flow.websocket;
}

function hasDnsResponse(
    flow: Flow,
): flow is DNSFlow & Required<Pick<DNSFlow, "response">> {
    return flow.type === "dns" && !!flow.response;
}

const RequestTab = Object.assign(() => <Request />, {
    displayName: Request.displayName,
});
const ResponseTab = Object.assign(() => <Response />, {
    displayName: Response.displayName,
});
const DnsRequestTab = Object.assign(() => <DnsRequest />, {
    displayName: DnsRequest.displayName,
});
const DnsResponseTab = Object.assign(
    ({ flow }: TabProps) => (hasDnsResponse(flow) ? <DnsResponse /> : null),
    {
        displayName: DnsResponse.displayName,
    },
);
const ErrorTab = Object.assign(
    ({ flow }: TabProps) => (hasError(flow) ? <Error flow={flow} /> : null),
    {
        displayName: Error.displayName,
    },
);
const WebSocketTab = Object.assign(
    ({ flow }: TabProps) =>
        hasWebSocket(flow) ? <WebSocket flow={flow} /> : null,
    {
        displayName: WebSocket.displayName,
    },
);
const TcpMessagesTab = Object.assign(
    ({ flow }: TabProps) =>
        flow.type === "tcp" ? <TcpMessages flow={flow} /> : null,
    {
        displayName: TcpMessages.displayName,
    },
);
const UdpMessagesTab = Object.assign(
    ({ flow }: TabProps) =>
        flow.type === "udp" ? <UdpMessages flow={flow} /> : null,
    {
        displayName: UdpMessages.displayName,
    },
);

export const allTabs: Record<
    TabId,
    FunctionComponent<TabProps> & { displayName?: string }
> = {
    request: RequestTab,
    response: ResponseTab,
    error: ErrorTab,
    connection: Connection,
    timing: Timing,
    websocket: WebSocketTab,
    tcpmessages: TcpMessagesTab,
    udpmessages: UdpMessagesTab,
    dnsrequest: DnsRequestTab,
    dnsresponse: DnsResponseTab,
    comment: Comment,
};

export function tabsForFlow(flow: Flow): TabId[] {
    let tabs: TabId[];
    switch (flow.type) {
        case "http":
            tabs = ["request"];
            if (flow.response) tabs.push("response");
            if (flow.websocket) tabs.push("websocket");
            break;
        case "tcp":
            tabs = ["tcpmessages"];
            break;
        case "udp":
            tabs = ["udpmessages"];
            break;
        case "dns":
            tabs = ["dnsrequest"];
            if (flow.response) tabs.push("dnsresponse");
            break;
    }

    if (flow.error) tabs.push("error");
    tabs.push("connection");
    tabs.push("timing");
    tabs.push("comment");
    return tabs;
}

export default function FlowView() {
    const dispatch = useAppDispatch();
    const flow = useAppSelector((state) => state.flows.selected[0]);
    let active = useAppSelector((state) => state.ui.flow.tab) as TabId;

    if (flow == undefined) {
        return <></>;
    }

    const tabs = tabsForFlow(flow);

    if (tabs.indexOf(active) < 0) {
        if (active === "response" && flow.error) {
            active = "error";
        } else if (
            active === "error" &&
            flow.type === "http" &&
            flow.response
        ) {
            active = "response";
        } else {
            active = tabs[0];
        }
    }
    const Tab = allTabs[active];

    return (
        <div className="flow-detail">
            <nav className="nav-tabs nav-tabs-sm">
                <button
                    data-testid="close-button-id"
                    className="close-button"
                    onClick={() => dispatch(flowsActions.select([]))}
                >
                    <i className="fa fa-times-circle"></i>
                </button>
                {tabs.map((tabId) => (
                    <a
                        key={tabId}
                        href="#"
                        className={classnames({ active: active === tabId })}
                        onClick={(event) => {
                            event.preventDefault();
                            dispatch(selectTab(tabId));
                        }}
                    >
                        {allTabs[tabId].displayName}
                    </a>
                ))}
            </nav>
            <Tab flow={flow} />
        </div>
    );
}
