import React, {PropTypes} from 'react'
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
