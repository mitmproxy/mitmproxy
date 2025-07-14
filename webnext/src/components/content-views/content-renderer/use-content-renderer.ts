import { useMemo } from "react";
import { CONTENT_VIEW_ALL_LINES } from "../use-content-view";

export type UseContentRendererParams = {
  content: string;
  contentType?: string;
  maxLines?: number;
  isExpanded: boolean;
};

export type UseContentRendererReturn = {
  language: string;
  formattedContent: string;
  displayContent: string;
  isTruncated: boolean;
};

function detectLanguage(content: string, contentType?: string): string {
  if (contentType) {
    if (contentType.includes("json")) return "json";
    if (contentType.includes("xml") || contentType.includes("html"))
      return "xml";
    if (contentType.includes("javascript")) return "javascript";
    if (contentType.includes("css")) return "css";
  }

  // Fallback detection.
  const trimmed = content.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) return "json";
  if (trimmed.startsWith("<")) return "xml";

  return "plaintext";
}

function formatContent(content: string, language: string): string {
  if (language === "json") {
    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      return content;
    }
  }

  return content;
}

function shouldTruncate(content: string, maxLines: number): boolean {
  return (
    maxLines !== CONTENT_VIEW_ALL_LINES && content.split("\n").length > maxLines
  );
}

export function useContentRenderer({
  content,
  contentType,
  maxLines = 20,
  isExpanded,
}: UseContentRendererParams): UseContentRendererReturn {
  return useMemo(() => {
    if (!content) {
      return {
        language: "plaintext",
        formattedContent: "",
        displayContent: "",
        isTruncated: false,
      };
    }

    const language = detectLanguage(content, contentType);
    const formattedContent = formatContent(content, language);
    const isTruncated = shouldTruncate(formattedContent, maxLines);
    const displayContent =
      isTruncated && !isExpanded
        ? formattedContent.split("\n").slice(0, maxLines).join("\n") + "\n..."
        : formattedContent;

    return {
      language,
      formattedContent,
      displayContent,
      isTruncated,
    };
  }, [content, contentType, maxLines, isExpanded]);
}
