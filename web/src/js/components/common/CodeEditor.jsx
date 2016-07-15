import React, { Component, PropTypes } from 'react'
import { render } from 'react-dom';
import Codemirror from 'react-codemirror';


export default class CodeEditor extends Component{
     static propTypes = {
        value: PropTypes.string.isRequired,
        onChange: PropTypes.func.isRequired,
    }

    render() {
        let options = {
            lineNumbers: true
        };
        return (
            <div onKeyDown={e => e.stopPropagation()}>
                <Codemirror value={this.props.value} onChange={this.props.onChange} options={options}/>
            </div>
        )
    }
}
