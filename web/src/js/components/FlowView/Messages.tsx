import type { Flow, MessagesMeta } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import * as React from "react";
import type { ContentViewData } from "../contentviews/useContentView";
import { useContentView } from "../contentviews/useContentView";
import ViewSelector from "../contentviews/ViewSelector";
import { setContentViewFor } from "../../ducks/ui/flow";
import { formatTimeStamp } from "../../utils";
import CodeEditor from "../contentviews/CodeEditor";
import Icon from "../common/Icon";

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
                const iconName = d.from_client ? "arrowRight" : "arrowLeft";
                const iconClassName = d.from_client
                    ? "text-primary"
                    : "text-danger";
                return (
                    <div key={i}>
                        <small>
                            <Icon name={iconName} className={iconClassName} />
                            <span className="float-right">
                                {d.timestamp && formatTimeStamp(d.timestamp)}
                            </span>
                        </small>
                        <CodeEditor
                            content={d.text}
                            language={d.syntax_highlight}
                            readonly
                        />
                    </div>
                );
            })}
        </div>
    );
}
