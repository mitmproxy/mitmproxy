import React, { Component, PropTypes } from 'react'
import { render } from 'react-dom';
import AceEditor from 'react-ace';

import 'brace/mode/javascript';
import 'brace/theme/kuroir';

export default class CodeEditor extends Component{
     static propTypes = {
        value: PropTypes.string.isRequired,
        onChange: PropTypes.func.isRequired,
    }

    render() {
        return (
            <div onKeyDown={e => e.stopPropagation()}>
                <AceEditor
                    mode="javascript"
                    theme="kuroir"
                    onChange={this.props.onChange}
                    name="rea"
                    value={this.props.value}
                    width="100%"
                    editorProps={{$blockScrolling: Infinity}}
                />
            </div>
        )
    }
}
