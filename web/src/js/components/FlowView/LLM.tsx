import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchApi } from "../../utils";
import type { HTTPFlow } from "../../flow";
import { useAppSelector } from "../../ducks";

// --- Types ---

interface LLMRequestData {
    model?: string;
    system?: string | null;
    messages: unknown[];
    tools: unknown[];
    parameters: Record<string, unknown>;
}

interface LLMResponseData {
    // Anthropic
    blocks?: {
        type: string;
        content: string;
        id?: string;
        name?: string;
        input?: unknown;
        signature?: string;
        tool_use_id?: string;
        caller?: unknown;
        block_content?: unknown[];
        citations?: unknown[];
    }[];
    stop_reason?: string;
    // OpenAI
    content?: string;
    tool_calls?: {
        id: string;
        function: { name: string; arguments: unknown };
    }[];
    finish_reason?: string;
    // Common
    model?: string;
    usage?: Record<string, unknown>;
    role?: string;
}

interface LLMData {
    provider: string | null;
    request: LLMRequestData | null;
    request_json: Record<string, unknown> | null;
    response: LLMResponseData | null;
    response_json: Record<string, unknown> | null;
    chat_messages: unknown[];
}

// --- Hook ---

function useLLMData(flowId: string): LLMData | undefined | "error" {
    const [data, setData] = useState<LLMData | undefined | "error">();

    useEffect(() => {
        const controller = new AbortController();
        fetchApi(`./flows/${flowId}/llm.json`, { signal: controller.signal })
            .then((response) => {
                if (!response.ok) throw new Error(`${response.status}`);
                return response.json();
            })
            .then((json) => setData(json as LLMData))
            .catch((e) => {
                if (!controller.signal.aborted) {
                    console.warn("Failed to load LLM data:", e);
                    setData("error");
                }
            });
        return () => controller.abort();
    }, [flowId]);

    return data;
}

// --- LLM Request Tab ---

export function LLMRequest() {
    const flow = useAppSelector((state) => state.flows.selected[0]) as HTTPFlow;
    const data = useLLMData(flow.id);

    if (!data || data === "error" || !data.request) {
        return (
            <section className="llm-tab">
                <div className="llm-loading">
                    {data === "error"
                        ? "Failed to load LLM data."
                        : "Loading..."}
                </div>
            </section>
        );
    }

    const req = data.request;
    const provider = data.provider || "unknown";

    return (
        <section className="llm-tab">
            <div className="llm-header">
                <span className="llm-provider">{provider}</span>
                <span className="llm-model">{req.model || "unknown"}</span>
            </div>

            {req.system && (
                <CollapsibleSection
                    title="System Prompt"
                    defaultCollapsed={true}
                >
                    {typeof req.system === "string" ? (
                        <pre className="llm-content">{req.system}</pre>
                    ) : (
                        <InlineJSON
                            data={req.system}
                            defaultCollapsed={false}
                        />
                    )}
                </CollapsibleSection>
            )}

            {req.tools && req.tools.length > 0 && (
                <CollapsibleSection
                    title={`Tools (${req.tools.length})`}
                    defaultCollapsed={true}
                >
                    {req.tools.map((tool: unknown, i: number) => {
                        const t = tool as Record<string, unknown>;
                        return (
                            <CollapsibleItem
                                key={i}
                                label={`[${i + 1}] ${(t.name as string) || "unnamed"}`}
                                defaultCollapsed={true}
                            >
                                {t.description != null && (
                                    <div className="llm-msg-part">
                                        <div className="llm-msg-part-label">
                                            description
                                        </div>
                                        <pre className="llm-item-content">
                                            {String(t.description)}
                                        </pre>
                                    </div>
                                )}
                                {t.input_schema != null && (
                                    <div className="llm-msg-part">
                                        <div className="llm-msg-part-label">
                                            input_schema
                                        </div>
                                        <InlineJSON data={t.input_schema} />
                                    </div>
                                )}
                            </CollapsibleItem>
                        );
                    })}
                </CollapsibleSection>
            )}

            {req.messages && req.messages.length > 0 && (
                <CollapsibleSection title={`Messages (${req.messages.length})`}>
                    {req.messages.map((msg: unknown, i: number) => {
                        const m = msg as Record<string, unknown>;
                        return (
                            <CollapsibleItem
                                key={i}
                                label={`[${i + 1}] ${(m.role as string) || "unknown"}`}
                            >
                                <MessageContent content={m.content} />
                            </CollapsibleItem>
                        );
                    })}
                </CollapsibleSection>
            )}
        </section>
    );
}
LLMRequest.displayName = "LLM Request";

// --- LLM Response Tab ---

export function LLMResponse() {
    const flow = useAppSelector((state) => state.flows.selected[0]) as HTTPFlow;
    const data = useLLMData(flow.id);

    if (!data || data === "error" || !data.response) {
        return (
            <section className="llm-tab">
                <div className="llm-loading">
                    {data === "error"
                        ? "Failed to load LLM data."
                        : !data
                          ? "Loading..."
                          : "No LLM response data."}
                </div>
            </section>
        );
    }

    const resp = data.response;
    const provider = data.provider || "unknown";

    return (
        <section className="llm-tab">
            <div className="llm-header">
                <span className="llm-provider">{provider}</span>
                <span className="llm-model">{resp.model || "unknown"}</span>
            </div>

            {/* Content blocks for Anthropic */}
            {resp.blocks && resp.blocks.length > 0 && (
                <CollapsibleSection
                    title={`Content Blocks (${resp.blocks.length})`}
                >
                    {resp.blocks.map((block, i) => (
                        <CollapsibleItem
                            key={i}
                            label={`[${i + 1}] ${block.type}${block.name ? ` ${block.name}` : ""}${block.id ? ` (${block.id})` : ""}${block.tool_use_id ? ` tool_use_id=${block.tool_use_id}` : ""}`}
                        >
                            {block.content && (
                                <pre className="llm-item-content">
                                    {block.content}
                                </pre>
                            )}
                            {block.input != null &&
                                block.input !== "" &&
                                (typeof block.input === "object" ? (
                                    <InlineJSON data={block.input} />
                                ) : (
                                    <pre className="llm-item-content">
                                        {String(block.input)}
                                    </pre>
                                ))}
                            {block.block_content != null &&
                                Array.isArray(block.block_content) &&
                                block.block_content.length > 0 && (
                                    <div className="llm-search-results">
                                        {block.block_content.map(
                                            (result: unknown, j: number) => {
                                                const r = result as Record<
                                                    string,
                                                    unknown
                                                >;
                                                return (
                                                    <div
                                                        key={j}
                                                        className="llm-search-result"
                                                    >
                                                        <div className="llm-search-result-title">
                                                            {r.title as string}
                                                        </div>
                                                        <div className="llm-search-result-url">
                                                            {r.url as string}
                                                        </div>
                                                    </div>
                                                );
                                            },
                                        )}
                                    </div>
                                )}
                        </CollapsibleItem>
                    ))}
                </CollapsibleSection>
            )}

            {/* Content for OpenAI */}
            {resp.content && (
                <CollapsibleSection title="Content">
                    <pre className="llm-content">{resp.content}</pre>
                </CollapsibleSection>
            )}

            {/* Tool calls for OpenAI */}
            {resp.tool_calls && resp.tool_calls.length > 0 && (
                <CollapsibleSection
                    title={`Tool Calls (${resp.tool_calls.length})`}
                >
                    {resp.tool_calls.map((tc, i) => (
                        <CollapsibleItem
                            key={i}
                            label={`[${i + 1}] ${tc.function.name} (${tc.id})`}
                        >
                            {typeof tc.function.arguments === "object" ? (
                                <InlineJSON data={tc.function.arguments} />
                            ) : (
                                <pre className="llm-item-content">
                                    {String(tc.function.arguments)}
                                </pre>
                            )}
                        </CollapsibleItem>
                    ))}
                </CollapsibleSection>
            )}

            {/* Stop/Finish reason */}
            {(resp.stop_reason || resp.finish_reason) && (
                <CollapsibleSection
                    title={resp.stop_reason ? "Stop Reason" : "Finish Reason"}
                >
                    <div className="llm-meta-value">
                        {resp.stop_reason || resp.finish_reason}
                    </div>
                </CollapsibleSection>
            )}
        </section>
    );
}
LLMResponse.displayName = "LLM Response";

// --- Collapsible JSON Viewer ---

function CopyableLeaf({
    className,
    display,
    copyText,
}: {
    className: string;
    display: string;
    copyText: string;
}) {
    const [copied, setCopied] = useState(false);

    const handleClick = useCallback(
        (e: React.MouseEvent) => {
            e.stopPropagation();
            navigator.clipboard.writeText(copyText).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
            });
        },
        [copyText],
    );

    return (
        <span
            className={`${className} json-leaf-copyable${copied ? " json-leaf-copied" : ""}`}
            onClick={handleClick}
            title={copied ? "Copied!" : "Click to copy"}
        >
            {display}
        </span>
    );
}

function JsonValue({
    value,
    defaultCollapsed,
}: {
    value: unknown;
    defaultCollapsed: boolean;
}) {
    if (value === null)
        return (
            <CopyableLeaf
                className="json-null"
                display="null"
                copyText="null"
            />
        );
    if (typeof value === "boolean")
        return (
            <CopyableLeaf
                className="json-boolean"
                display={String(value)}
                copyText={String(value)}
            />
        );
    if (typeof value === "number")
        return (
            <CopyableLeaf
                className="json-number"
                display={String(value)}
                copyText={String(value)}
            />
        );
    if (typeof value === "string")
        return (
            <CopyableLeaf
                className="json-string"
                display={`"${value}"`}
                copyText={value}
            />
        );
    if (Array.isArray(value))
        return <JsonArray items={value} defaultCollapsed={defaultCollapsed} />;
    if (typeof value === "object")
        return (
            <JsonObject
                obj={value as Record<string, unknown>}
                defaultCollapsed={defaultCollapsed}
            />
        );
    return <span>{String(value)}</span>;
}

function JsonObject({
    obj,
    defaultCollapsed,
}: {
    obj: Record<string, unknown>;
    defaultCollapsed: boolean;
}) {
    const [collapsed, setCollapsed] = useState(defaultCollapsed);
    const entries = Object.entries(obj);
    const toggle = useCallback(() => setCollapsed((c) => !c), []);

    if (entries.length === 0) return <span>{"{}"}</span>;

    if (collapsed) {
        return (
            <span>
                <span className="json-toggle" onClick={toggle}>
                    {"\u25B6"}{" "}
                </span>
                <span className="json-bracket">{"{"}</span>
                <span className="json-collapsed-hint">
                    {" "}
                    {entries.length}{" "}
                    {entries.length === 1 ? "key" : "keys"}{" "}
                </span>
                <span className="json-bracket">{"}"}</span>
            </span>
        );
    }

    return (
        <span>
            <span className="json-toggle" onClick={toggle}>
                {"\u25BC"}{" "}
            </span>
            <span className="json-bracket">{"{"}</span>
            <div className="json-indent">
                {entries.map(([key, val], i) => (
                    <div key={key} className="json-entry">
                        <span className="json-key">{`"${key}"`}</span>
                        <span className="json-colon">: </span>
                        <JsonValue value={val} defaultCollapsed={true} />
                        {i < entries.length - 1 && <span>,</span>}
                    </div>
                ))}
            </div>
            <span className="json-bracket">{"}"}</span>
        </span>
    );
}

function JsonArray({
    items,
    defaultCollapsed,
}: {
    items: unknown[];
    defaultCollapsed: boolean;
}) {
    const [collapsed, setCollapsed] = useState(defaultCollapsed);
    const toggle = useCallback(() => setCollapsed((c) => !c), []);

    if (items.length === 0) return <span>{"[]"}</span>;

    if (collapsed) {
        return (
            <span>
                <span className="json-toggle" onClick={toggle}>
                    {"\u25B6"}{" "}
                </span>
                <span className="json-bracket">[</span>
                <span className="json-collapsed-hint">
                    {" "}
                    {items.length} {items.length === 1 ? "item" : "items"}{" "}
                </span>
                <span className="json-bracket">]</span>
            </span>
        );
    }

    return (
        <span>
            <span className="json-toggle" onClick={toggle}>
                {"\u25BC"}{" "}
            </span>
            <span className="json-bracket">[</span>
            <div className="json-indent">
                {items.map((item, i) => (
                    <div key={i} className="json-entry">
                        <JsonValue value={item} defaultCollapsed={true} />
                        {i < items.length - 1 && <span>,</span>}
                    </div>
                ))}
            </div>
            <span className="json-bracket">]</span>
        </span>
    );
}

function CollapsibleJSON({ data }: { data: unknown }) {
    return (
        <pre className="llm-json json-viewer">
            <JsonValue value={data} defaultCollapsed={false} />
        </pre>
    );
}

function InlineJSON({
    data,
    defaultCollapsed = true,
}: {
    data: unknown;
    defaultCollapsed?: boolean;
}) {
    return (
        <div className="llm-inline-json json-viewer">
            <JsonValue value={data} defaultCollapsed={defaultCollapsed} />
        </div>
    );
}

// --- LLM Request JSON Tab ---

export function LLMRequestJSON() {
    const flow = useAppSelector((state) => state.flows.selected[0]) as HTTPFlow;
    const data = useLLMData(flow.id);

    if (!data || data === "error" || !data.request_json) {
        return (
            <section className="llm-tab">
                <div className="llm-loading">
                    {data === "error"
                        ? "Failed to load LLM data."
                        : !data
                          ? "Loading..."
                          : "No LLM request JSON."}
                </div>
            </section>
        );
    }

    return (
        <section className="llm-tab">
            <CollapsibleJSON data={data.request_json} />
        </section>
    );
}
LLMRequestJSON.displayName = "LLM Request JSON";

// --- LLM Response JSON Tab ---

export function LLMResponseJSON() {
    const flow = useAppSelector((state) => state.flows.selected[0]) as HTTPFlow;
    const data = useLLMData(flow.id);

    if (!data || data === "error" || !data.response_json) {
        return (
            <section className="llm-tab">
                <div className="llm-loading">
                    {data === "error"
                        ? "Failed to load LLM data."
                        : !data
                          ? "Loading..."
                          : "No LLM response JSON."}
                </div>
            </section>
        );
    }

    return (
        <section className="llm-tab">
            <CollapsibleJSON data={data.response_json} />
        </section>
    );
}
LLMResponseJSON.displayName = "LLM Response JSON";

// --- Copy Button ---

function CopyButton({
    targetRef,
}: {
    targetRef: React.RefObject<HTMLElement | null>;
}) {
    const [copied, setCopied] = useState(false);

    const handleCopy = useCallback(
        (e: React.MouseEvent) => {
            e.stopPropagation();
            const text = targetRef.current?.innerText ?? "";
            navigator.clipboard.writeText(text).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
            });
        },
        [targetRef],
    );

    return (
        <span
            className={`llm-copy-btn${copied ? " llm-copy-btn-copied" : ""}`}
            onClick={handleCopy}
            title="Copy"
        >
            {copied ? "\u2713" : "\u2398"}
        </span>
    );
}

// --- Collapsible Section ---

function CollapsibleSection({
    title,
    defaultCollapsed = false,
    children,
}: {
    title: string;
    defaultCollapsed?: boolean;
    children: React.ReactNode;
}) {
    const [collapsed, setCollapsed] = useState(defaultCollapsed);
    const bodyRef = useRef<HTMLDivElement>(null);
    const toggle = useCallback(() => setCollapsed((c) => !c), []);

    return (
        <div className="llm-section">
            <h5
                className="llm-section-title llm-section-toggle"
                onClick={toggle}
            >
                <span className="llm-toggle-icon">
                    {collapsed ? "\u25B6" : "\u25BC"}
                </span>
                <span className="llm-section-title-text">{title}</span>
                {!collapsed && <CopyButton targetRef={bodyRef} />}
            </h5>
            {!collapsed && (
                <div className="llm-section-body" ref={bodyRef}>
                    {children}
                </div>
            )}
        </div>
    );
}

// --- Collapsible Item (for array elements inside a section) ---

function CollapsibleItem({
    label,
    defaultCollapsed = false,
    children,
}: {
    label: string;
    defaultCollapsed?: boolean;
    children: React.ReactNode;
}) {
    const [collapsed, setCollapsed] = useState(defaultCollapsed);
    const bodyRef = useRef<HTMLDivElement>(null);
    const toggle = useCallback(() => setCollapsed((c) => !c), []);

    return (
        <div className="llm-item">
            <div className="llm-item-header" onClick={toggle}>
                <span className="llm-toggle-icon">
                    {collapsed ? "\u25B6" : "\u25BC"}
                </span>
                <span className="llm-item-header-text">{label}</span>
                {!collapsed && <CopyButton targetRef={bodyRef} />}
            </div>
            {!collapsed && (
                <div className="llm-item-body" ref={bodyRef}>
                    {children}
                </div>
            )}
        </div>
    );
}

// --- Message Content Renderer ---

function MessageContent({ content }: { content: unknown }) {
    if (typeof content === "string")
        return <pre className="llm-item-content">{content}</pre>;
    if (Array.isArray(content)) {
        return (
            <>
                {content.map((part: unknown, i: number) => (
                    <MessagePart
                        key={i}
                        part={part as Record<string, unknown>}
                    />
                ))}
            </>
        );
    }
    if (typeof content === "object" && content !== null)
        return <InlineJSON data={content} />;
    return <pre className="llm-item-content">{String(content)}</pre>;
}

function MessagePart({ part }: { part: Record<string, unknown> }) {
    const ptype = (part.type as string) || "text";
    switch (ptype) {
        case "text":
            return (
                <div className="llm-msg-part">
                    <div className="llm-msg-part-label">text</div>
                    <pre className="llm-item-content">
                        {part.text as string}
                    </pre>
                </div>
            );
        case "tool_use":
            return (
                <div className="llm-msg-part">
                    <div className="llm-msg-part-label">
                        tool_use: {part.name as string}
                    </div>
                    {part.input != null && <InlineJSON data={part.input} />}
                </div>
            );
        case "tool_result":
            return (
                <div className="llm-msg-part">
                    <div className="llm-msg-part-label">
                        tool_result
                        {part.tool_use_id ? `: ${part.tool_use_id}` : ""}
                    </div>
                    {typeof part.content === "string" ? (
                        <pre className="llm-item-content">{part.content}</pre>
                    ) : part.content != null ? (
                        <InlineJSON data={part.content} />
                    ) : null}
                </div>
            );
        case "image":
        case "image_url":
            return <div className="llm-msg-part-label">[image]</div>;
        case "thinking":
            return (
                <div className="llm-msg-part">
                    <div className="llm-msg-part-label">thinking</div>
                    <pre className="llm-item-content">
                        {(part.thinking || part.text) as string}
                    </pre>
                </div>
            );
        default:
            return (
                <div className="llm-msg-part">
                    <div className="llm-msg-part-label">{ptype}</div>
                    {part.text != null && (
                        <pre className="llm-item-content">
                            {part.text as string}
                        </pre>
                    )}
                </div>
            );
    }
}
