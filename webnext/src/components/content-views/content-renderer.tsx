"use client";

import { memo, useCallback, useMemo, useState, useRef } from "react";
import Editor, { type OnMount } from "@monaco-editor/react";
import { editor as EditorType } from "monaco-editor/esm/vs/editor/editor.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LuCopy, LuDownload } from "react-icons/lu";
import { VscWordWrap } from "react-icons/vsc";
import { useDarkMode } from "usehooks-ts";
import { formatBytes } from "@/components/content-views/utils";
import { cn } from "@/lib/utils";

export type ContentRendererProps = {
  content: string;
  part: "request" | "response";
  maxLines?: number;
  showMore?: () => void;
  contentType?: string;
};

export const ContentRenderer = memo<ContentRendererProps>(
  ({ content, maxLines = 20, showMore, contentType, part }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isWrapped, setIsWrapped] = useState(false);
    const editorRef = useRef<EditorType.IStandaloneCodeEditor>(null);
    const { isDarkMode } = useDarkMode();

    const { language, formattedContent, displayContent, isTruncated } =
      useMemo(() => {
        if (!content)
          return {
            language: "plaintext",
            formattedContent: "",
            displayContent: "",
            isTruncated: false,
          };

        const lang = detectLanguage(content, contentType);
        const formatted = formatContent(content, lang);
        const truncated = shouldTruncate(formatted, maxLines);
        const display =
          truncated && !isExpanded
            ? formatted.split("\n").slice(0, maxLines).join("\n") + "\n..."
            : formatted;

        return {
          language: lang,
          formattedContent: formatted,
          displayContent: display,
          isTruncated: truncated,
        };
      }, [content, contentType, maxLines, isExpanded]);

    const editorOptions = useMemo<EditorType.IEditorOptions>(
      () => ({
        readOnly: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: isWrapped ? "on" : "off",
        lineNumbers: "on",
        glyphMargin: false,
        folding: true,
        lineDecorationsWidth: 0,
        lineNumbersMinChars: 3,
        renderLineHighlight: "none",
        scrollbar: {
          vertical: "auto",
          horizontal: "auto",
          verticalScrollbarSize: 8,
          horizontalScrollbarSize: 8,
        },
        fontSize: 13,
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
        automaticLayout: true,
        contextmenu: false,
        theme: isDarkMode ? "vs-dark" : "vs",
      }),
      [isWrapped, isDarkMode],
    );

    const handleEditorDidMount = useCallback<OnMount>(
      (editor) => {
        editorRef.current = editor;
        editor.updateOptions({
          ...editorOptions,
          renderValidationDecorations: "off",
        });
      },
      [editorOptions],
    );

    const handleCopy = useCallback(async () => {
      try {
        await navigator.clipboard.writeText(formattedContent);
      } catch (err) {
        console.error("Failed to copy content:", err);
      }
    }, [formattedContent]);

    const handleDownload = useCallback(() => {
      const blob = new Blob([formattedContent], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${part}-body.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, [formattedContent, part]);

    const handleToggleExpand = useCallback(() => {
      setIsExpanded((prev) => !prev);
      showMore?.();
    }, [showMore]);

    const handleToggleWrap = useCallback(() => {
      setIsWrapped((prev) => !prev);
    }, []);

    const contentBytes = useMemo(
      () => formatBytes(new Blob([content]).size),
      [content],
    );

    if (!content || content.length === 0) {
      return (
        <Card className="p-4">
          <div className="text-muted-foreground text-center text-sm">
            No content to display
          </div>
        </Card>
      );
    }

    return (
      <div className="h-full min-h-0 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs">
              {`${language.toUpperCase()}${contentType ? ` (${contentType})` : ""}`}
            </span>
          </div>

          <div className="text-muted-foreground flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleToggleWrap}
              title="Toggle word wrap"
              className={cn({ border: isWrapped })}
            >
              <VscWordWrap />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void handleCopy}
              title="Copy contents"
            >
              <LuCopy />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              title="Download contents"
            >
              <LuDownload /> {contentBytes}
              <span className="text-xs">{}</span>
            </Button>
          </div>
        </div>

        {/* The editor takes up all available space minus the height of the top bar. */}
        <div className="relative h-[calc(100%_-_32px)] min-h-0">
          <Editor
            height="100%"
            language={language}
            value={displayContent}
            options={editorOptions}
            onMount={handleEditorDidMount}
            theme={isDarkMode ? "vs-dark" : "vs"}
            loading={
              <div className="flex h-32 items-center justify-center">
                <div className="text-muted-foreground text-sm">
                  Loading editor...
                </div>
              </div>
            }
          />

          {/* Expand/Collapse button for truncated content */}
          {isTruncated && (
            <div className="absolute right-2 bottom-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleToggleExpand}
                className="shadow-md"
              >
                {isExpanded
                  ? "Show Less"
                  : `Show More (${formattedContent.split("\n").length - maxLines} more lines)`}
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  },
);
ContentRenderer.displayName = "ContentRenderer";

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
  return content.split("\n").length > maxLines;
}
