import {HTTPFlow, WebSocketData} from "../../flow";
import * as React from "react";
import {useCallback, useMemo, useState} from "react";
import {ContentViewData, SHOW_MAX_LINES, useContent} from "../contentviews/useContent";
import {MessageUtils} from "../../flow/utils";
import ViewSelector from "../contentviews/ViewSelector";
import {useAppDispatch, useAppSelector} from "../../ducks";
import {setContentViewFor} from "../../ducks/ui/flow";
import LineRenderer from "../contentviews/LineRenderer";
import {formatTimeStamp} from "../../utils";


export default function WebSocket({flow}: { flow: HTTPFlow & { websocket: WebSocketData } }) {
    const dispatch = useAppDispatch();

    const contentView = useAppSelector(state => state.ui.flow.contentViewFor[flow.id + "ws"] || "Auto");
    let [maxLines, setMaxLines] = useState<number>(SHOW_MAX_LINES);
    const showMore = useCallback(() => setMaxLines(Math.max(1024, maxLines * 2)), [maxLines]);
    const content = useContent(
        MessageUtils.getContentURL(flow, "messages", contentView, maxLines + 1),
        flow.id + flow.websocket.messages_meta.count
    );
    const messages = useMemo<ContentViewData[] | undefined>(() => content && JSON.parse(content), [content]) || [];

    return (
        <section className="websocket">
            <h4>WebSocket</h4>
            <div className="contentview">
                <div className="controls">
                    <h5>{flow.websocket.messages_meta.count} Messages</h5>
                    <ViewSelector value={contentView}
                                  onChange={cv => dispatch(setContentViewFor(flow.id + "ws", cv))}/>
                </div>
                {messages.map((d: ContentViewData, i) => {
                    const className = `fa fa-fw fa-arrow-${d.from_client ? "right text-primary" : "left text-danger"}`;
                    const renderer = <div key={i}>
                        <small>
                            <i className={className}/>
                            <span className="pull-right">{d.timestamp && formatTimeStamp(d.timestamp)}</span>
                        </small>
                        <LineRenderer lines={d.lines} maxLines={maxLines} showMore={showMore}/>
                    </div>;
                    maxLines -= d.lines.length;
                    return renderer;
                })}
            </div>
            <CloseSummary websocket={flow.websocket}/>
        </section>
    )
}
WebSocket.displayName = "WebSocket"


function CloseSummary({websocket}: {websocket: WebSocketData}){
    if(!websocket.timestamp_end)
        return null;
    const reason = websocket.close_reason ? `(${websocket.close_reason})` : ""
    return <div>
        <i className="fa fa-fw fa-window-close text-muted"/>
        &nbsp;
        Closed by {websocket.closed_by_client ? "client": "server"} with code {websocket.close_code} {reason}.

        <small className="pull-right">
        {formatTimeStamp(websocket.timestamp_end)}
        </small>
    </div>
}
