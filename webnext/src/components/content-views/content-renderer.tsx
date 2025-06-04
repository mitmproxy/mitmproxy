"use client";

import { useState, useRef } from "react";
import Editor, { type OnMount } from "@monaco-editor/react";
import { editor as EditorType } from "monaco-editor/esm/vs/editor/editor.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LuCopy, LuDownload } from "react-icons/lu";
import { VscWordWrap } from "react-icons/vsc";
import { formatBytes } from "@/components/content-views/utils";
import { cn } from "@/lib/utils";
import { CONTENT_VIEW_ALL_LINES } from "@/components/content-views/use-content-view";
import { useTheme } from "@/hooks/use-theme";

export type ContentRendererProps = {
  content: string;
  part: "request" | "response";
  maxLines?: number;
  showMore?: () => void;
  showAll?: () => void;
  contentType?: string;
};

export function ContentRenderer({
  content,
  maxLines = 20,
  contentType,
  part,
  showMore,
  showAll,
}: ContentRendererProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isWrapped, setIsWrapped] = useState(false);
  const editorRef = useRef<EditorType.IStandaloneCodeEditor>(null);
  const { isDarkMode } = useTheme();

  const { language, formattedContent, displayContent, isTruncated } =
    processContent({ content, contentType, maxLines, isExpanded });

  const editorOptions: EditorType.IEditorOptions &
    EditorType.IGlobalEditorOptions = {
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
  };

  const handleEditorDidMount: OnMount = (editor) => {
    editorRef.current = editor;
    editor.updateOptions({
      ...editorOptions,
      renderValidationDecorations: "off",
    });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedContent);
    } catch (err) {
      console.error("Failed to copy content:", err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([formattedContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${part}-body.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleToggleExpand = () => {
    setIsExpanded((prev) => !prev);
    showMore?.();
  };

  const handleToggleExpandAll = () => {
    setIsExpanded((prev) => !prev);
    showAll?.();
  };

  const handleToggleWrap = () => {
    setIsWrapped((prev) => !prev);
  };

  const contentBytes = formatBytes(new Blob([content]).size);

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
          <div className="absolute right-2 bottom-2 mr-4 space-y-2 space-x-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleToggleExpand}
              className="shadow-md"
            >
              Show more
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleToggleExpandAll}
              className="shadow-md"
            >
              Show all
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

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

function processContent({
  content,
  contentType,
  maxLines = 20,
  isExpanded,
}: Pick<ContentRendererProps, "content" | "contentType" | "maxLines"> & {
  isExpanded: boolean;
}) {
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
}
