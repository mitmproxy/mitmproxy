import { HTTPFlow, WebSocketData } from "../../flow";
import * as React from "react";
import { formatTimeStamp } from "../../utils";
import Messages from "./Messages";

export default function WebSocket({
    flow,
}: {
    flow: HTTPFlow & { websocket: WebSocketData };
}) {
    return (
        <section className="websocket">
            <h4>WebSocket</h4>
            <Messages
                flow={flow}
                messages_meta={flow.websocket.messages_meta}
            />
            <CloseSummary websocket={flow.websocket} />
        </section>
    );
}
WebSocket.displayName = "WebSocket";

function CloseSummary({ websocket }: { websocket: WebSocketData }) {
    if (!websocket.timestamp_end) return null;
    const reason = websocket.close_reason ? `(${websocket.close_reason})` : "";
    return (
        <div>
            <i className="fa fa-fw fa-window-close text-muted" />
            &nbsp; Closed by {websocket.closed_by_client
                ? "client"
                : "server"}{" "}
            with code {websocket.close_code} {reason}.
            <small className="pull-right">
                {formatTimeStamp(websocket.timestamp_end)}
            </small>
        </div>
    );
}
