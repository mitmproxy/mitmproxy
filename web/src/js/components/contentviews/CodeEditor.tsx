import * as React from "react";
import { Component } from "react";
import CodeMirror from "../../contrib/CodeMirror";

type CodeEditorProps = {
    initialContent: string;
};

export default class CodeEditor extends Component<CodeEditorProps> {
    private editor = React.createRef<CodeMirror>();

    getContent = (): string => {
        return this.editor.current?.codeMirror.getValue();
    };

    render = () => {
        const options = {
            lineNumbers: true,
        };
        return (
            <div className="codeeditor" onKeyDown={(e) => e.stopPropagation()}>
                <CodeMirror
                    ref={this.editor}
                    value={this.props.initialContent}
                    onChange={() => 0}
                    options={options}
                />
            </div>
        );
    };
}
