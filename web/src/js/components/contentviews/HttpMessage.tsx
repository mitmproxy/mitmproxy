import React, { useEffect, useRef, useState } from "react";
import { HTTPFlow, HTTPMessage } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setContentViewFor } from "../../ducks/ui/flow";
import { ContentViewData, useContentView } from "./useContentView";
import { MessageUtils } from "../../flow/utils";
import FileChooser from "../common/FileChooser";
import * as flowActions from "../../ducks/flows";
import { uploadContent } from "../../ducks/flows";
import Button from "../common/Button";
import ViewSelector from "./ViewSelector";
import { copyViewContentDataToClipboard, fetchApi } from "../../utils";
import ContentEditor from "./ContentEditor";

type HttpMessageProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
};

export default function HttpMessage({ flow, message }: HttpMessageProps) {
    return <HttpMessageView flow={flow} message={message} />;
}

type HttpMessageViewProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
};

function HttpMessageView({ flow, message }: HttpMessageViewProps) {
    const dispatch = useAppDispatch();
    const part = flow.request === message ? "request" : "response";
    const contentView = useAppSelector(
        (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
    );
    const [editedContent, setEditedContent] = useState<string>();
    const [shouldSave, setShouldSave] = useState(false);

    const contentViewData = useContentView(
        flow,
        message,
        contentView,
        undefined,
        message.contentHash,
    );

    // These refs store the latest values of editedContent and contentViewData.
    // They're needed because the keyboard event listener (added outside React's render cycle)
    // captures its own closure and won't automatically get the updated values from state.
    // Using refs allows the latest values to be accessed reliably inside the event handler.
    const editedContentRef = useRef(editedContent);
    const contentViewDataRef = useRef(contentViewData);

    let desc: string;
    if (message.contentLength === 0) {
        desc = "No content";
    } else if (contentViewData === undefined) {
        desc = "Loading...";
    } else {
        desc =
            `${contentViewData.view_name} ${contentViewData.description}`.trimEnd();
    }

    useEffect(() => {
        editedContentRef.current = editedContent;
        contentViewDataRef.current = contentViewData;
    }, [editedContent, contentViewData]);

    useEffect(() => {
        setShouldSave(editedContent !== contentViewData?.text);
    }, [editedContent]);

    useEffect(() => {
        const handleKeyDown = async (event: KeyboardEvent) => {
            // Cmd + s or Ctrl + s to save the content
            const isCmdOrCtrl = event.metaKey || event.ctrlKey;
            if (isCmdOrCtrl && event.key.toLowerCase() === "s") {
                event.preventDefault();
                await saveContent();
            }
        };

        window.addEventListener("keydown", handleKeyDown, true);

        return () => {
            window.removeEventListener("keydown", handleKeyDown, true);
        };
    }, []);

    const saveContent = async () => {
        await dispatch(
            flowActions.update(flow, {
                [part]: {
                    content:
                        editedContentRef.current ||
                        contentViewDataRef.current?.text ||
                        "",
                },
            }),
        ).then(() => setShouldSave(false));
    };

    return (
        <div className="contentview" key="view">
            <div className="controls">
                <div>
                    <h5>{desc}</h5>
                    {shouldSave && (
                        <i className="fa fa-circle" aria-hidden="true"></i>
                    )}
                </div>
                {shouldSave && (
                    <Button
                        onClick={saveContent}
                        icon="fa-floppy-o"
                        className="btn-xs"
                    >
                        Save
                    </Button>
                )}
                &nbsp;
                {contentViewData && contentViewData?.text.length > 0 && (
                    <CopyButton flow={flow} message={message} />
                )}
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
            <ContentEditor
                content={contentViewData?.text ?? ""}
                language={contentViewData?.syntax_highlight}
                onChange={(content) => setEditedContent(content)}
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
