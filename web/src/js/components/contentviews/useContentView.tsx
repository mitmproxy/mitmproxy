import { useMemo } from "react";
import { useContent } from "./useContent";
import { Flow, HTTPFlow, HTTPMessage } from "../../flow";
import { MessageUtils } from "../../flow/utils";
import { SyntaxHighlight } from "../../backends/consts";

export type ContentViewData = {
    text: string;
    view_name: string;
    syntax_highlight: SyntaxHighlight;
    description: string;
    from_client?: boolean;
    timestamp?: number;
};

export function useContentView(
    flow: Flow,
    part: "messages",
    view?: string,
    hash?: string,
): ContentViewData[] | undefined;

export function useContentView(
    flow: HTTPFlow,
    part: HTTPMessage | "request" | "response",
    view?: string,
    hash?: string,
): ContentViewData | undefined;

export function useContentView(
    flow: Flow,
    part: HTTPMessage | "request" | "response" | "messages",
    view?: string,
    hash?: string,
): ContentViewData | ContentViewData[] | undefined {
    const url = MessageUtils.getContentURL(flow, part, view);
    const cv_json = useContent(url, hash);
    return useMemo<ContentViewData | undefined>(() => {
        if (cv_json) {
            try {
                return JSON.parse(cv_json);
            } catch {
                const err: ContentViewData = {
                    text: cv_json,
                    description: "Network Error",
                    syntax_highlight: SyntaxHighlight.ERROR,
                    view_name: "raw",
                };
                if (part === "messages") {
                    return [err];
                } else {
                    return err;
                }
            }
        } else {
            return undefined;
        }
    }, [cv_json]);
}
