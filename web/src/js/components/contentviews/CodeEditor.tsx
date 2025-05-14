import * as React from "react";
import { useCallback, useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { javascript } from "@codemirror/lang-javascript";
import { yaml } from "@codemirror/lang-yaml";
import { css } from "@codemirror/lang-css";
import { html } from "@codemirror/lang-html";

type CodeEditorProps = {
    initialContent: string;
    onChange: (content: string) => void;
    readonly?: boolean;
    language?: "javascript" | "yaml" | "css" | "html";
};

export default function CodeEditor({
    initialContent,
    onChange,
    language,
    readonly = false,
}: CodeEditorProps) {
    const stopPropagation = useCallback(
        (e: React.KeyboardEvent<HTMLDivElement>) => e.stopPropagation(),
        [],
    );
    const extensions = useMemo(() => {
        switch (language) {
            case "javascript":
                return [javascript()];
            case "yaml":
                return [yaml()];
            case "css":
                return [css()];
            case "html":
                return [html()];
            default:
                return [];
        }
    }, [language]);
    return (
        <div className="codeeditor" onKeyDown={stopPropagation}>
            <CodeMirror
                value={initialContent}
                onChange={onChange}
                readOnly={readonly}
                extensions={extensions}
            />
        </div>
    );
}
