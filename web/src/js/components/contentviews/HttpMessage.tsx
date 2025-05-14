import React, { useCallback, useState } from "react";
import { HTTPFlow, HTTPMessage } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setContentViewFor } from "../../ducks/ui/flow";
import { ContentViewData, useContentView } from "./useContentView";
import { useContent } from "./useContent";
import { MessageUtils } from "../../flow/utils";
import FileChooser from "../common/FileChooser";
import * as flowActions from "../../ducks/flows";
import { uploadContent } from "../../ducks/flows";
import Button from "../common/Button";
import CodeEditor from "./CodeEditor";
import ContentRenderer from "./ContentRenderer";
import ViewSelector from "./ViewSelector";
import { copyViewContentDataToClipboard, fetchApi } from "../../utils";

type HttpMessageProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
};

export default function HttpMessage({ flow, message }: HttpMessageProps) {
    const [isEdited, setIsEdited] = useState<boolean>(false);
    if (isEdited) {
        return (
            <HttpMessageEdit
                flow={flow}
                message={message}
                stopEdit={() => setIsEdited(false)}
            />
        );
    } else {
        return (
            <HttpMessageView
                flow={flow}
                message={message}
                startEdit={() => setIsEdited(true)}
            />
        );
    }
}

type HttpMessageEditProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
    stopEdit: () => void;
};

function HttpMessageEdit({ flow, message, stopEdit }: HttpMessageEditProps) {
    const dispatch = useAppDispatch();

    const part = flow.request === message ? "request" : "response";
    const url = MessageUtils.getContentURL(flow, message);
    const content = useContent(url, message.contentHash);
    const [editedContent, setEditedContent] = useState<string>();

    const save = async () => {
        await dispatch(
            flowActions.update(flow, {
                [part]: { content: editedContent || content || "" },
            }),
        );
        stopEdit();
    };
    return (
        <div className="contentview" key="edit">
            <div className="controls">
                <h5>[Editing]</h5>
                <Button
                    onClick={save}
                    icon="fa-check text-success"
                    className="btn-xs"
                >
                    Done
                </Button>
                &nbsp;
                <Button
                    onClick={() => stopEdit()}
                    icon="fa-times text-danger"
                    className="btn-xs"
                >
                    Cancel
                </Button>
            </div>
            <CodeEditor
                initialContent={content || ""}
                onChange={setEditedContent}
            />
        </div>
    );
}

type HttpMessageViewProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
    startEdit: () => void;
};

function HttpMessageView({ flow, message, startEdit }: HttpMessageViewProps) {
    const dispatch = useAppDispatch();
    const part = flow.request === message ? "request" : "response";
    const contentView = useAppSelector(
        (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
    );

    const [maxLines, setMaxLines] = useState<number>(
        useAppSelector((state) => state.options.content_view_lines_cutoff),
    );
    const showMore = useCallback(
        () => setMaxLines(Math.max(1024, maxLines * 2)),
        [maxLines],
    );

    const contentViewData = useContentView(
        flow,
        message,
        contentView,
        maxLines + 1,
        message.contentHash,
    );

    let desc: string;
    if (message.contentLength === 0) {
        desc = "No content";
    } else if (contentViewData === undefined) {
        desc = "Loading...";
    } else {
        desc =
            `${contentViewData.view_name} ${contentViewData.description}`.trimEnd();
    }

    return (
        <div className="contentview" key="view">
            <div className="controls">
                <h5>{desc}</h5>
                {contentViewData && contentViewData?.text.length > 0 && (
                    <CopyButton flow={flow} message={message} />
                )}
                &nbsp;
                <Button onClick={startEdit} icon="fa-edit" className="btn-xs">
                    Edit
                </Button>
                &nbsp;
                <FileChooser
                    icon="fa-upload"
                    text="Replace"
                    title="Upload a file to replace the content."
                    onOpenFile={(content) =>
                        dispatch(uploadContent(flow, content, part))
                    }
                    className="btn btn-default btn-xs"
                />
                &nbsp;
                <ViewSelector
                    value={contentView}
                    onChange={(cv) =>
                        dispatch(
                            setContentViewFor({
                                messageId: flow.id + part,
                                contentView: cv,
                            }),
                        )
                    }
                />
            </div>
            {ViewImage.matches(message) && (
                <ViewImage flow={flow} message={message} />
            )}
            <ContentRenderer
                content={contentViewData?.text ?? ""}
                maxLines={maxLines}
                showMore={showMore}
            />
        </div>
    );
}

type CopyButtonProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
};

function CopyButton({ flow, message }: CopyButtonProps) {
    const part = flow.request === message ? "request" : "response";
    const contentView = useAppSelector(
        (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
    );

    const [isCopied, setIsCopied] = useState<boolean>(false);
    const [isFetchingFullContent, setIsFetchingFullContent] =
        useState<boolean>(false);

    const handleClickCopyButton = async () => {
        try {
            const url = MessageUtils.getContentURL(flow, message, contentView);
            setIsFetchingFullContent(true);

            const response = await fetchApi(url);
            if (!response.ok) {
                throw new Error(
                    `${response.status} ${response.statusText}`.trim(),
                );
            }

            const data: ContentViewData = await response.json();

            await copyViewContentDataToClipboard(data);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
        } catch (e) {
            console.error(e);
        } finally {
            setIsFetchingFullContent(false);
        }
    };

    return (
        <Button
            onClick={handleClickCopyButton}
            icon="fa-clipboard"
            className="btn-xs"
            disabled={isFetchingFullContent}
        >
            {isCopied ? "Copied!" : "Copy"}
        </Button>
    );
}

const isImage =
    /^image\/(png|jpe?g|gif|webp|vnc.microsoft.icon|x-icon|svg\+xml)$/i;
ViewImage.matches = (msg) =>
    isImage.test(MessageUtils.getContentType(msg) || "");

type ViewImageProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
};

export function ViewImage({ flow, message }: ViewImageProps) {
    return (
        <div className="flowview-image">
            <img
                src={MessageUtils.getContentURL(flow, message)}
                alt="preview"
                className="img-thumbnail"
            />
        </div>
    );
}
