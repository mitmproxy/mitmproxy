import React, { useCallback, useEffect, useRef, useState } from "react";
import type { HTTPFlow, HTTPMessage } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setContentViewFor } from "../../ducks/ui/flow";
import type { ContentViewData } from "./useContentView";
import { useContentView } from "./useContentView";
import { useContent } from "./useContent";
import { MessageUtils } from "../../flow/utils";
import FileChooser from "../common/FileChooser";
import * as flowActions from "../../ducks/flows";
import { uploadContent } from "../../ducks/flows";
import Button from "../common/Button";
import CodeEditor from "./CodeEditor";
import ContentRenderer from "./ContentRenderer";
import ViewSelector from "./ViewSelector";
import {
    copyToClipboard,
    copyViewContentDataToClipboard,
    fetchApi,
} from "../../utils";
import { SyntaxHighlight } from "../../backends/consts";

type HttpMessageProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
};

export default function HttpMessage({ flow, message }: HttpMessageProps) {
    const [isEdited, setIsEdited] = useState<boolean>(false);
    const [usePrettifiedForCopyEdit, setUsePrettifiedForCopyEdit] =
        useState<boolean>(false);
    if (isEdited) {
        return (
            <HttpMessageEdit
                flow={flow}
                message={message}
                usePrettifiedForCopyEdit={usePrettifiedForCopyEdit}
                stopEdit={() => setIsEdited(false)}
            />
        );
    } else {
        return (
            <HttpMessageView
                flow={flow}
                message={message}
                usePrettifiedForCopyEdit={usePrettifiedForCopyEdit}
                setUsePrettifiedForCopyEdit={setUsePrettifiedForCopyEdit}
                startEdit={() => setIsEdited(true)}
            />
        );
    }
}

type HttpMessageEditProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
    usePrettifiedForCopyEdit: boolean;
    stopEdit: () => void;
};

function HttpMessageEdit({
    flow,
    message,
    usePrettifiedForCopyEdit,
    stopEdit,
}: HttpMessageEditProps) {
    const dispatch = useAppDispatch();

    const part = flow.request === message ? "request" : "response";
    const contentView = useAppSelector(
        (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
    );
    const url = MessageUtils.getContentURL(
        flow,
        message,
        usePrettifiedForCopyEdit ? contentView : undefined,
    );
    const fetchedContent = useContent(url, message.contentHash);
    const contentViewData: ContentViewData | undefined = (() => {
        if (!usePrettifiedForCopyEdit || !fetchedContent) {
            return undefined;
        }
        try {
            return JSON.parse(fetchedContent);
        } catch {
            return undefined;
        }
    })();
    const [editedContent, setEditedContent] = useState<string>();

    const editorLanguage = (() => {
        if (!usePrettifiedForCopyEdit) {
            return null;
        }
        const sh = contentViewData?.syntax_highlight;
        if (!sh) {
            return null;
        }
        switch (sh) {
            case "css":
                return SyntaxHighlight.CSS;
            case "javascript":
                return SyntaxHighlight.JAVASCRIPT;
            case "xml":
                return SyntaxHighlight.XML;
            case "yaml":
                return SyntaxHighlight.YAML;
            case "none":
                return SyntaxHighlight.NONE;
            case "error":
                return SyntaxHighlight.ERROR;
            default:
                return null;
        }
    })();

    const initialContent = usePrettifiedForCopyEdit
        ? (contentViewData?.text ?? fetchedContent ?? "")
        : (fetchedContent ?? "");
    const editorValue = editedContent ?? initialContent;

    const maybeReencodeGraphQL = (input: string): string | undefined => {
        if (!usePrettifiedForCopyEdit) {
            return undefined;
        }
        if (contentViewData?.view_name?.toLowerCase() !== "graphql") {
            return undefined;
        }
        const delimiter = "\n---\n";
        const idx = input.indexOf(delimiter);
        if (idx === -1) {
            return undefined;
        }
        const headerText = input.slice(0, idx).trim();
        const queryText = input.slice(idx + delimiter.length);
        try {
            const header = JSON.parse(headerText);
            if (
                header &&
                typeof header === "object" &&
                !Array.isArray(header)
            ) {
                header.query = queryText;
                return JSON.stringify(header);
            }
        } catch {
            return undefined;
        }
        return undefined;
    };

    const save = async () => {
        const contentToSave = maybeReencodeGraphQL(editorValue) ?? editorValue;
        await dispatch(
            flowActions.update(flow, {
                [part]: { content: contentToSave },
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
                initialContent={editorValue}
                onChange={setEditedContent}
                language={editorLanguage}
            />
        </div>
    );
}

type HttpMessageViewProps = {
    flow: HTTPFlow;
    message: HTTPMessage;
    usePrettifiedForCopyEdit: boolean;
    setUsePrettifiedForCopyEdit: (value: boolean) => void;
    startEdit: () => void;
};

function HttpMessageView({
    flow,
    message,
    usePrettifiedForCopyEdit,
    setUsePrettifiedForCopyEdit,
    startEdit,
}: HttpMessageViewProps) {
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
                    <>
                        <CopyButton
                            flow={flow}
                            message={message}
                            usePrettifiedForCopyEdit={usePrettifiedForCopyEdit}
                        />
                        &nbsp;
                        <Button
                            onClick={() =>
                                setUsePrettifiedForCopyEdit(
                                    !usePrettifiedForCopyEdit,
                                )
                            }
                            icon={
                                usePrettifiedForCopyEdit
                                    ? "fa-check text-success"
                                    : "fa-indent"
                            }
                            className="btn-xs"
                            title={
                                usePrettifiedForCopyEdit
                                    ? "Copy/Edit uses formatted view output"
                                    : "Use formatted view output for Copy/Edit"
                            }
                        >
                            {usePrettifiedForCopyEdit ? "Formatted" : "Format"}
                        </Button>
                    </>
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
    usePrettifiedForCopyEdit: boolean;
};

function CopyButton({
    flow,
    message,
    usePrettifiedForCopyEdit,
}: CopyButtonProps) {
    const part = flow.request === message ? "request" : "response";
    const contentView = useAppSelector(
        (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
    );

    const [isCopied, setIsCopied] = useState<boolean>(false);
    const [isFetchingFullContent, setIsFetchingFullContent] =
        useState<boolean>(false);
    const copiedTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(
        undefined,
    );

    useEffect(() => {
        return () => {
            if (copiedTimeout.current) {
                clearTimeout(copiedTimeout.current);
            }
        };
    }, []);

    const handleClickCopyButton = async () => {
        try {
            const url = MessageUtils.getContentURL(
                flow,
                message,
                usePrettifiedForCopyEdit ? contentView : undefined,
            );
            setIsFetchingFullContent(true);

            const response = await fetchApi(url);
            if (!response.ok) {
                throw new Error(
                    `${response.status} ${response.statusText}`.trim(),
                );
            }

            if (usePrettifiedForCopyEdit) {
                const data: ContentViewData = await response.json();
                await copyViewContentDataToClipboard(data);
            } else {
                await copyToClipboard(response.text());
            }
            setIsCopied(true);
            if (copiedTimeout.current) {
                clearTimeout(copiedTimeout.current);
            }
            copiedTimeout.current = setTimeout(() => setIsCopied(false), 1200);
        } catch (e) {
            console.error(e);
        } finally {
            setIsFetchingFullContent(false);
        }
    };

    if (isCopied) {
        return (
            <span className="text-success" title="Copied">
                <i className="fa fa-check text-success" />
                &nbsp;Copied
            </span>
        );
    }

    return (
        <Button
            onClick={handleClickCopyButton}
            icon="fa-clipboard"
            className="btn-xs"
            disabled={isFetchingFullContent}
        >
            Copy
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
