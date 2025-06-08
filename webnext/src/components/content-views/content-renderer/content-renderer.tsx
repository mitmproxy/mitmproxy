"use client";

import { useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { json } from "@codemirror/lang-json";
import { xml } from "@codemirror/lang-xml";
import { javascript } from "@codemirror/lang-javascript";
import { css } from "@codemirror/lang-css";
import { vscodeDark, vscodeLight } from "@uiw/codemirror-theme-vscode";
import { EditorView } from "@codemirror/view";
import { EditorState, type Extension } from "@codemirror/state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LuCopy, LuDownload } from "react-icons/lu";
import { VscWordWrap } from "react-icons/vsc";
import { cn } from "@/lib/utils";
import { useContentRenderer } from "./use-content-renderer";
import { formatBytes } from "@/components/content-views/utils";
import { useTheme } from "@/components/theme-provider";

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
  const { resolvedTheme } = useTheme();
  const { language, formattedContent, displayContent, isTruncated } =
    useContentRenderer({
      content,
      contentType,
      maxLines,
      isExpanded,
    });

  const extensions = getExtensions({ language, isWrapped });
  const contentBytes = formatBytes(new Blob([content]).size);

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
            onClick={() => void handleCopy()}
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
        <div className="h-full overflow-scroll">
          <CodeMirror
            value={displayContent}
            height="100%"
            extensions={extensions}
            theme={resolvedTheme === "dark" ? vscodeDark : vscodeLight}
            editable={false}
            basicSetup={{
              lineNumbers: true,
              foldGutter: true,
              dropCursor: false,
              allowMultipleSelections: false,
              indentOnInput: false,
              bracketMatching: true,
              closeBrackets: false,
              autocompletion: false,
              highlightSelectionMatches: false,
              searchKeymap: true,
            }}
          />
        </div>

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

function getExtensions({
  isWrapped,
  language,
}: {
  language: string;
  isWrapped: boolean;
}): Extension[] {
  const extensions: Extension[] = [
    EditorView.theme({
      "&": {
        fontSize: "13px",
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
      },
      ".cm-content": {
        padding: "12px",
        minHeight: "100px",
      },
      ".cm-focused": {
        outline: "none",
      },
      ".cm-editor": {
        borderRadius: "0",
        height: "100%",
      },
      ".cm-scroller": {
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
      },
    }),
    EditorState.readOnly.of(true),
  ];

  switch (language) {
    case "json":
      extensions.push(json());
      break;
    case "xml":
      extensions.push(xml());
      break;
    case "javascript":
      extensions.push(javascript());
      break;
    case "css":
      extensions.push(css());
      break;
    default:
      // No specific language extension needed.
      break;
  }

  if (isWrapped) {
    extensions.push(EditorView.lineWrapping);
  }

  return extensions;
}
