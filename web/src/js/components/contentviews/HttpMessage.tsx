import React, { useCallback, useEffect, useState } from "react";
import type { HTTPFlow, HTTPMessage } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setContentViewFor } from "../../ducks/ui/flow";
import type { ContentViewData } from "./useContentView";
import { useContentView } from "./useContentView";
import { MessageUtils } from "../../flow/utils";
import FileChooser from "../common/FileChooser";
import * as flowActions from "../../ducks/flows";
import { uploadContent } from "../../ducks/flows";
import Button from "../common/Button";
import Icon from "../common/Icon";
import CodeEditor from "./CodeEditor";
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

    const originalText = contentViewData?.text ?? "";
    // `undefined` means "not edited yet"; the editor still shows originalText.
    const [editedContent, setEditedContent] = useState<string>();
    const isEdited =
        editedContent !== undefined && editedContent !== originalText;

    // Reset local edits whenever the underlying content changes (new flow,
    // new content view, or content reloaded from the backend).
    useEffect(() => {
        setEditedContent(undefined);
    }, [contentView, message.contentHash, flow.id, part]);

    const saveContent = useCallback(() => {
        if (editedContent === undefined) return;
        dispatch(
            flowActions.update(flow, {
                [part]: { content: editedContent },
            }),
        );
    }, [dispatch, flow, part, editedContent]);

    let desc: string;
    if (message.contentLength === 0) {
        desc = "No content";
    } else if (contentViewData === undefined) {
        desc = "Loading...";
    } else {
        desc =
            `${contentViewData.view_name} ${contentViewData.description}`.trimEnd();
    }

    // Preserve the "Show more" cutoff behavior: the backend returns at most
    // maxLines + 1 lines, so more than maxLines lines means content is truncated.
    const isTruncated = originalText.split("\n").length > maxLines;

    return (
        <div className="contentview" key="view">
            <div className="controls">
                <div className="desc">
                    <h5>{desc}</h5>
                    {isEdited && (
                        <span
                            className="unsaved-indicator"
                            title="Unsaved changes"
                            aria-label="Unsaved changes"
                        />
                    )}
                </div>
                {isEdited && (
                    <>
                        <Button
                            onClick={saveContent}
                            icon="save"
                            iconClassName="text-success"
                            className="btn-xs"
                            title="Save changes (Ctrl/Cmd+S)"
                        >
                            Save
                        </Button>
                        &nbsp;
                    </>
                )}
                {contentViewData && contentViewData?.text.length > 0 && (
                    <CopyButton flow={flow} message={message} />
                )}
                &nbsp;
                <FileChooser
                    icon="upload"
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
            {contentViewData !== undefined && (
                // Render the editor once the content view has loaded, even when
                // the body is empty, so empty requests/responses can be edited.
                <CodeEditor
                    key={`${flow.id}-${part}-${contentView}-${message.contentHash}`}
                    content={originalText}
                    language={contentViewData.syntax_highlight}
                    onChange={setEditedContent}
                    onSave={saveContent}
                />
            )}
            {isTruncated && (
                <button
                    onClick={showMore}
                    className="btn btn-xs btn-info show-more"
                >
                    <Icon name="expandMore" /> Show more
                </button>
            )}
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
            icon="clipboard"
            className="btn-xs"
            disabled={isFetchingFullContent}
        >
            {isCopied ? "Copied!" : "Copy"}
        </Button>
    );
}

const isImage =
    /^image\/(png|jpe?g|gif|webp|avif|vnd\.microsoft\.icon|x-icon|svg\+xml)$/i;
ViewImage.matches = (msg: HTTPMessage) =>
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
