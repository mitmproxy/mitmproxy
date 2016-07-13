import React, { Component, PropTypes } from 'react'
import { render } from 'react-dom';
import brace from 'brace';
import AceEditor from 'react-ace';
import Button from './Button'


import 'brace/mode/javascript';
import 'brace/mode/json';
import 'brace/theme/monokai';




export default class CodeEditor extends Component{
    constructor( props ) {
        super(props)
        this.state = {value: this.props.value}
    }

    onChange(newValue) {
        this.setState({value: newValue})
    }

    render() {
        return (
            <div onKeyDown={e => e.stopPropagation()}>
                <AceEditor
                    onChange={e => this.onChange(e)}
                    mode="javascript"
                    theme="monokai"
                    value={this.state.value}
                    width="100%"
                    name="codeEditor"
                    editorProps={{$blockScrolling: Infinity}}
                />
                <Button onClick={(e) => this.props.onSave(this.state.value)} text="Update"/>
            </div>
        )
    }
}
