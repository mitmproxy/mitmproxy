import * as React from "react";
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
import {
    selectTab,
    selectRequestTab,
    selectResponseTab,
} from "../ducks/ui/flow";
import { useAppDispatch, useAppSelector } from "../ducks";
import type {
    Error as FlowError,
    Flow,
    HTTPFlow,
    WebSocketData,
} from "../flow";
import classnames from "classnames";
import TcpMessages from "./FlowView/TcpMessages";
import UdpMessages from "./FlowView/UdpMessages";
import * as flowsActions from "../ducks/flows";
import Icon from "./common/Icon";
import Splitter from "./common/Splitter";

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

export const tabLabels: Record<TabId, string> = {
    request: Request.displayName,
    response: Response.displayName,
    error: Error.displayName,
    connection: Connection.displayName,
    timing: Timing.displayName,
    websocket: WebSocket.displayName,
    tcpmessages: TcpMessages.displayName,
    udpmessages: UdpMessages.displayName,
    dnsrequest: DnsRequest.displayName,
    dnsresponse: DnsResponse.displayName,
    comment: Comment.displayName,
};

function renderTab(active: TabId, flow: Flow): React.ReactElement | null {
    switch (active) {
        case "request":
            return <Request />;
        case "response":
            return <Response />;
        case "error":
            return flow.error ? (
                <Error flow={flow as Flow & { error: FlowError }} />
            ) : null;
        case "connection":
            return <Connection flow={flow} />;
        case "timing":
            return <Timing flow={flow} />;
        case "websocket":
            return flow.type === "http" && flow.websocket ? (
                <WebSocket
                    flow={
                        flow as HTTPFlow & {
                            websocket: WebSocketData;
                        }
                    }
                />
            ) : null;
        case "tcpmessages":
            return flow.type === "tcp" ? <TcpMessages flow={flow} /> : null;
        case "udpmessages":
            return flow.type === "udp" ? <UdpMessages flow={flow} /> : null;
        case "dnsrequest":
            return <DnsRequest />;
        case "dnsresponse":
            return flow.type === "dns" && flow.response ? (
                <DnsResponse />
            ) : null;
        case "comment":
            return <Comment flow={flow} />;
    }
}

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

function CloseButton() {
    const dispatch = useAppDispatch();
    return (
        <button
            data-testid="close-button-id"
            className="close-button"
            onClick={() => dispatch(flowsActions.select([]))}
        >
            <Icon name="closeCircle" />
        </button>
    );
}

function TabStrip({
    tabs,
    active,
    onSelect,
    children,
}: {
    tabs: TabId[];
    active: TabId | undefined;
    onSelect: (tab: TabId) => void;
    children?: React.ReactNode;
}) {
    return (
        <nav className="nav-tabs nav-tabs-sm">
            {children}
            {tabs.map((tabId) => (
                <a
                    key={tabId}
                    href="#"
                    className={classnames({ active: active === tabId })}
                    onClick={(event) => {
                        event.preventDefault();
                        onSelect(tabId);
                    }}
                >
                    {tabLabels[tabId]}
                </a>
            ))}
        </nav>
    );
}

/** Request-side tabs of the split HTTP view. */
function requestTabsForFlow(flow: HTTPFlow): TabId[] {
    const tabs: TabId[] = ["request"];
    if (flow.error) tabs.push("error");
    tabs.push("connection", "timing", "comment");
    return tabs;
}

/** Response-side tabs of the split HTTP view. */
function responseTabsForFlow(flow: HTTPFlow): TabId[] {
    const tabs: TabId[] = [];
    if (flow.response) tabs.push("response");
    if (flow.websocket) tabs.push("websocket");
    return tabs;
}

function SplitHttpView({ flow }: { flow: HTTPFlow }) {
    const dispatch = useAppDispatch();
    const tabRequest = useAppSelector(
        (state) => state.ui.flow.tabRequest,
    ) as TabId;
    const tabResponse = useAppSelector(
        (state) => state.ui.flow.tabResponse,
    ) as TabId;

    const requestTabs = requestTabsForFlow(flow);
    const responseTabs = responseTabsForFlow(flow);

    const activeRequest = requestTabs.includes(tabRequest)
        ? tabRequest
        : requestTabs[0];
    const activeResponse = responseTabs.includes(tabResponse)
        ? tabResponse
        : responseTabs[0];

    return (
        <div className="flow-detail flow-detail-split">
            <div className="flow-detail-panels">
                <div className="flow-detail-panel">
                    <TabStrip
                        tabs={requestTabs}
                        active={activeRequest}
                        onSelect={(t) => dispatch(selectRequestTab(t))}
                    >
                        <CloseButton />
                    </TabStrip>
                    {renderTab(activeRequest, flow)}
                </div>
                <Splitter axis="x" />
                <div className="flow-detail-panel">
                    <TabStrip
                        tabs={responseTabs}
                        active={activeResponse}
                        onSelect={(t) => dispatch(selectResponseTab(t))}
                    />
                    {activeResponse ? (
                        renderTab(activeResponse, flow)
                    ) : (
                        <div className="flow-detail-empty text-muted">
                            Waiting for response…
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function SingleColumnView({ flow }: { flow: Flow }) {
    const dispatch = useAppDispatch();
    let active = useAppSelector((state) => state.ui.flow.tab) as TabId;

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

    return (
        <div className="flow-detail">
            <TabStrip
                tabs={tabs}
                active={active}
                onSelect={(t) => dispatch(selectTab(t))}
            >
                <CloseButton />
            </TabStrip>
            {renderTab(active, flow)}
        </div>
    );
}

export default function FlowView() {
    const flow = useAppSelector((state) => state.flows.selected[0]);

    if (flow == undefined) {
        return <></>;
    }
    if (flow.type === "http") {
        return <SplitHttpView flow={flow} />;
    }
    return <SingleColumnView flow={flow} />;
}
