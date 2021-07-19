import React from 'react'
import CodeMirror from "../../contrib/CodeMirror"


type CodeEditorProps = {
    content: string,
    onChange: Function,
}

export default function CodeEditor ( { content, onChange}: CodeEditorProps ){

    let options = {
        lineNumbers: true
    };
    return (
        <div className="codeeditor" onKeyDown={e => e.stopPropagation()}>
            <CodeMirror value={content} onChange={onChange} options={options}/>
        </div>
    )
}
