import React, { Component, PropTypes } from 'react'
import { render } from 'react-dom';
import Codemirror from 'react-codemirror';


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
            <Codemirror value={content} onChange={onChange} options={options}/>
        </div>
    )
}
