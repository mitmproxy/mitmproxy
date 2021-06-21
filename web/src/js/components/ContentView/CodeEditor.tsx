import React from 'react'
import PropTypes from 'prop-types'
import CodeMirror from "../../contrib/CodeMirror"


CodeEditor.propTypes = {
        content: PropTypes.string.isRequired,
        onChange: PropTypes.func.isRequired,
}

export default function CodeEditor ( { content, onChange} ){

    let options = {
        lineNumbers: true
    };
    return (
        <div className="codeeditor" onKeyDown={e => e.stopPropagation()}>
            <CodeMirror value={content} onChange={onChange} options={options}/>
        </div>
    )
}
