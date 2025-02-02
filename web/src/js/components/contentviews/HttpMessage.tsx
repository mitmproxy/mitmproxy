import React, { useCallback, useMemo, useRef, useState } from "react";
import { HTTPFlow, HTTPMessage } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setContentViewFor } from "../../ducks/ui/flow";
import { ContentViewData, useContent } from "./useContent";
import { MessageUtils } from "../../flow/utils";
import FileChooser from "../common/FileChooser";
import * as flowActions from "../../ducks/flows";
import { uploadContent } from "../../ducks/flows";
import Button from "../common/Button";
import CodeEditor from "./CodeEditor";
import LineRenderer from "./LineRenderer";
import ViewSelector from "./ViewSelector";
import { copyViewContentDataToClipboard, fetchApi } from "../../utils";

type HttpMessageProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
};

export default function HttpMessage({ flow, message }: HttpMessageProps) {
    const dispatch = useAppDispatch();
    const part = flow.request === message ? "request" : "response";
    const contentView = useAppSelector(
        (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
    );
    const editorRef = useRef<CodeEditor>(null);
    const [maxLines, setMaxLines] = useState<number>(
        useAppSelector((state) => state.options.content_view_lines_cutoff),
    );
    const showMore = useCallback(
        () => setMaxLines(Math.max(1024, maxLines * 2)),
        [maxLines],
    );
    const [isEdited, setIsEdited] = useState<boolean>(false);
    const [isCopied, setIsCopied] = useState<boolean>(false);
    const [isFetchingFullContent, setIsFetchingFullContent] =
        useState<boolean>(false);

    let url: string;
    if (isEdited) {
        url = MessageUtils.getContentURL(flow, message);
    } else {
        url = MessageUtils.getContentURL(
            flow,
            message,
            contentView,
            maxLines + 1,
        );
    }
    const content = useContent(url, message.contentHash);
    const contentViewData = useMemo<ContentViewData | undefined>(() => {
        if (content && !isEdited) {
            try {
                return JSON.parse(content);
            } catch (e) {
                const err: ContentViewData = {
                    description: "Network Error",
                    lines: [[["error", `${content}`]]],
                };
                return err;
            }
        } else {
            return undefined;
        }
    }, [content]);

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

    if (isEdited) {
        const save = async () => {
            const content = editorRef.current?.getContent();
            await dispatch(flowActions.update(flow, { [part]: { content } }));
            setIsEdited(false);
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
                        onClick={() => setIsEdited(false)}
                        icon="fa-times text-danger"
                        className="btn-xs"
                    >
                        Cancel
                    </Button>
                </div>
                <CodeEditor ref={editorRef} initialContent={content || ""} />
            </div>
        );
    } else {
        const desc = contentViewData
            ? contentViewData.description
            : "Loading...";
        return (
            <div className="contentview" key="view">
                <div className="controls">
                    <h5>{desc}</h5>
                    {contentViewData && contentViewData?.lines.length > 0 && (
                        <Button
                            onClick={handleClickCopyButton}
                            icon="fa-clipboard"
                            className="btn-xs"
                            disabled={isFetchingFullContent}
                        >
                            {isCopied ? "Copied!" : "Copy"}
                        </Button>
                    )}
                    &nbsp;
                    <Button
                        onClick={() => setIsEdited(true)}
                        icon="fa-edit"
                        className="btn-xs"
                    >
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
                <LineRenderer
                    lines={contentViewData?.lines || []}
                    maxLines={maxLines}
                    showMore={showMore}
                />
            </div>
        );
    }
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
