import {Flow, MessagesMeta} from "../../flow";
import {useAppDispatch, useAppSelector} from "../../ducks";
import * as React from "react";
import {useCallback, useMemo, useState} from "react";
import {ContentViewData, SHOW_MAX_LINES, useContent} from "../contentviews/useContent";
import {MessageUtils} from "../../flow/utils";
import ViewSelector from "../contentviews/ViewSelector";
import {setContentViewFor} from "../../ducks/ui/flow";
import {formatTimeStamp} from "../../utils";
import LineRenderer from "../contentviews/LineRenderer";

type MessagesPropTypes = {
    flow: Flow
    messages_meta: MessagesMeta
}

export default function Messages({flow, messages_meta}: MessagesPropTypes) {
    const dispatch = useAppDispatch();

    const contentView = useAppSelector(state => state.ui.flow.contentViewFor[flow.id + "messages"] || "Auto");
    let [maxLines, setMaxLines] = useState<number>(SHOW_MAX_LINES);
    const showMore = useCallback(() => setMaxLines(Math.max(1024, maxLines * 2)), [maxLines]);
    const content = useContent(
        MessageUtils.getContentURL(flow, "messages", contentView, maxLines + 1),
        flow.id + messages_meta.count
    );
    const messages = useMemo<ContentViewData[] | undefined>(() => content && JSON.parse(content), [content]) || [];

    return (
        <div className="contentview">
            <div className="controls">
                <h5>{messages_meta.count} Messages</h5>
                <ViewSelector value={contentView}
                              onChange={cv => dispatch(setContentViewFor(flow.id + "messages", cv))}/>
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
    )
}
