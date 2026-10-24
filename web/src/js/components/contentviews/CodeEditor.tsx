import * as React from "react";
import { useCallback, useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { css } from "@codemirror/lang-css";
import { html } from "@codemirror/lang-html";
import { javascript } from "@codemirror/lang-javascript";
import { yaml } from "@codemirror/lang-yaml";
import { oneDark } from "@codemirror/theme-one-dark";
import { keymap } from "@codemirror/view";
import { Prec } from "@codemirror/state";
import type { Extension } from "@codemirror/state";
import { SyntaxHighlight } from "../../backends/consts";
import { useResolvedTheme } from "../helpers/useTheme";

type CodeEditorProps = {
    content: string;
    onChange: (content: string) => void;
    readonly?: boolean;
    language?: SyntaxHighlight | null;
    /**
     * Invoked when the user presses Cmd/Ctrl+S while the editor is focused.
     * The binding is scoped to this editor instance, so only the focused
     * editor reacts to the shortcut.
     */
    onSave?: () => void;
};

export default function CodeEditor({
    content,
    onChange,
    language,
    readonly = false,
    onSave,
}: CodeEditorProps) {
    const resolvedTheme = useResolvedTheme();
    const stopPropagation = useCallback(
        (e: React.KeyboardEvent<HTMLDivElement>) => e.stopPropagation(),
        [],
    );
    const extensions = useMemo(() => {
        const result: Extension[] = [];
        if (onSave) {
            // Scope the save shortcut to the focused editor via a high-precedence
            // keymap so it takes priority over CodeMirror's default bindings.
            result.push(
                Prec.highest(
                    keymap.of([
                        {
                            key: "Mod-s",
                            preventDefault: true,
                            run: () => {
                                onSave();
                                return true;
                            },
                        },
                    ]),
                ),
            );
        }
        switch (language) {
            case SyntaxHighlight.YAML:
                result.push(yaml());
                break;
            case SyntaxHighlight.XML:
                result.push(html());
                break;
            case SyntaxHighlight.JAVASCRIPT:
                result.push(javascript());
                break;
            case SyntaxHighlight.CSS:
                result.push(css());
                break;
            case undefined:
            case null:
            case SyntaxHighlight.NONE:
            case SyntaxHighlight.ERROR:
                break;
            /* istanbul ignore next @preserve */
            default: {
                const unexpected: never = language;
                console.error(
                    "Unexpected syntax highlighting language: ",
                    unexpected,
                );
            }
        }
        return result;
    }, [language, onSave]);
    return (
        <div className="codeeditor" onKeyDown={stopPropagation}>
            <CodeMirror
                value={content}
                onChange={onChange}
                readOnly={readonly}
                extensions={extensions}
                theme={resolvedTheme === "dark" ? oneDark : "light"}
                basicSetup={{
                    highlightActiveLine: false,
                }}
            />
        </div>
    );
}
