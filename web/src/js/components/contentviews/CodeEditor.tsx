import * as React from "react";
import {useCallback} from "react";
import CodeMirror from '@uiw/react-codemirror';

type CodeEditorProps = {
    initialContent: string;
    onChange: (content: string) => void;
};

export default function CodeEditor({initialContent, onChange}: CodeEditorProps) {
    const stopPropagation = useCallback(
        (e: React.KeyboardEvent<HTMLDivElement>) => e.stopPropagation(),
        []
    );
    return <div className="codeeditor" onKeyDown={stopPropagation}>
        <CodeMirror value={initialContent} onChange={onChange} />
    </div>;
}
