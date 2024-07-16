import * as React from "react";
import { FunctionComponent } from "react";
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
import { Flow } from "../flow";
import classnames from "classnames";
import TcpMessages from "./FlowView/TcpMessages";
import UdpMessages from "./FlowView/UdpMessages";
import * as flowsActions from "../ducks/flows";

type TabProps = {
    flow: Flow;
};

export const allTabs: {
    [name: string]: FunctionComponent<TabProps> & { displayName: string };
} = {
    request: Request,
    response: Response,
    error: Error,
    connection: Connection,
    timing: Timing,
    websocket: WebSocket,
    tcpmessages: TcpMessages,
    udpmessages: UdpMessages,
    dnsrequest: DnsRequest,
    dnsresponse: DnsResponse,
    comment: Comment,
};

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

export default function FlowView() {
    const dispatch = useAppDispatch();
    const flow = useAppSelector(
        (state) => state.flows.byId[state.flows.selected[0]],
    );
    let active = useAppSelector((state) => state.ui.flow.tab);

    if (flow == undefined) {
        return <></>;
    }

    const tabs = tabsForFlow(flow);

    if (tabs.indexOf(active) < 0) {
        if (active === "response" && flow.error) {
            active = "error";
        } else if (active === "error" && "response" in flow) {
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
                    onClick={() => dispatch(flowsActions.select(undefined))}
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
