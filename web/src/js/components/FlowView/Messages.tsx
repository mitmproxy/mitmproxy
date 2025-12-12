import { Flow, MessagesMeta } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import * as React from "react";
import {
    ContentViewData,
    useContentView,
} from "../contentviews/useContentView";
import ViewSelector from "../contentviews/ViewSelector";
import { setContentViewFor } from "../../ducks/ui/flow";
import { formatTimeStamp } from "../../utils";
import ContentEditor from "../contentviews/ContentEditor";

type MessagesPropTypes = {
    flow: Flow;
    messages_meta: MessagesMeta;
};

export default function Messages({ flow, messages_meta }: MessagesPropTypes) {
    const dispatch = useAppDispatch();

    const contentView = useAppSelector(
        (state) => state.ui.flow.contentViewFor[flow.id + "messages"] || "Auto",
    );
    const messages =
        useContentView(
            flow,
            "messages",
            contentView,
            flow.id + messages_meta.count,
        ) ?? [];

    return (
        <div className="contentview">
            <div className="controls">
                <h5>{messages_meta.count} Messages</h5>
                <ViewSelector
                    value={contentView}
                    onChange={(cv) =>
                        dispatch(
                            setContentViewFor({
                                messageId: flow.id + "messages",
                                contentView: cv,
                            }),
                        )
                    }
                />
            </div>
            {messages.map((d: ContentViewData, i) => {
                const className = `fa fa-fw fa-arrow-${
                    d.from_client ? "right text-primary" : "left text-danger"
                }`;
                const renderer = (
                    <div key={i}>
                        <small>
                            <i className={className} />
                            <span className="pull-right">
                                {d.timestamp && formatTimeStamp(d.timestamp)}
                            </span>
                        </small>
                        <ContentEditor
                            initialContent={d.text}
                            language={d.syntax_highlight}
                            readonly
                        />
                    </div>
                );
                return renderer;
            })}
        </div>
    );
}
