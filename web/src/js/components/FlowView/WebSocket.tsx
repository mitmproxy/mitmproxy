import type { HTTPFlow, WebSocketData } from "../../flow";
import * as React from "react";
import { useTranslation } from "react-i18next";
import { formatTimeStamp } from "../../utils";
import Messages from "./Messages";

export default function WebSocket({
    flow,
}: {
    flow: HTTPFlow & { websocket: WebSocketData };
}) {
    const { t } = useTranslation();
    return (
        <section className="websocket">
            <h4>{t("flowView.webSocket.title")}</h4>
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
    const { t } = useTranslation();
    if (!websocket.timestamp_end) return null;
    const reason = websocket.close_reason ? `(${websocket.close_reason})` : "";
    return (
        <div>
            <i className="fa fa-fw fa-window-close text-muted" />
            &nbsp; {t("flowView.webSocket.closedBy", {
                who: websocket.closed_by_client ? t("flowView.webSocket.client") : t("flowView.webSocket.server"),
                code: websocket.close_code,
                reason,
            })}
            <small className="pull-right">
                {formatTimeStamp(websocket.timestamp_end)}
            </small>
        </div>
    );
}
