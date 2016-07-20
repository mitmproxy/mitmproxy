import React, { Component, PropTypes } from 'react'
import { render } from 'react-dom';
import Codemirror from 'react-codemirror';


export default class CodeEditor extends Component{
     static propTypes = {
        content: PropTypes.string.isRequired,
        onChange: PropTypes.func.isRequired,
    }

    constructor(props){
        super(props)
    }

    componentWillMount(){
        this.props.onChange(this.props.content)
    }

    render() {
        let options = {
            lineNumbers: true
        };
        return (
            <div onKeyDown={e => e.stopPropagation()}>
                <Codemirror value={this.props.content} onChange={this.props.onChange} options={options}/>
            </div>
        )
    }
}
