import * as React from "react";
import { useCallback, useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { javascript } from "@codemirror/lang-javascript";
import { yaml } from "@codemirror/lang-yaml";
import { css } from "@codemirror/lang-css";
import { html } from "@codemirror/lang-html";

type ContentEditorProps = {
    content: string;
    onChange: (content: string) => void;
    readonly?: boolean;
    language?: string;
};

export default function ContentEditor({
    content,
    onChange,
    language,
    readonly = false,
}: ContentEditorProps) {
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
                return [html()];
        }
    }, [language]);
    
    return (
        <div className="codeeditor" onKeyDown={stopPropagation}>
            <CodeMirror
                value={content}
                onChange={onChange}
                readOnly={readonly}
                extensions={extensions}
                basicSetup={{ highlightActiveLine: false }}
            />
        </div>
    );
}
