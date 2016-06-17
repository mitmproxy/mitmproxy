import React, { Component, PropTypes } from 'react'
import ReactDOM from 'react-dom'
import ValidateEditor from './ValueEditor/ValidateEditor'

export default class ValueEditor extends Component {

    static contextTypes = {
        returnFocus: PropTypes.func,
    }

    static propTypes = {
        content: PropTypes.string.isRequired,
        onDone: PropTypes.func.isRequired,
        inline: PropTypes.bool,
    }

    constructor(props) {
        super(props)
        this.focus = this.focus.bind(this)
    }

    render() {
        var tag = this.props.inline ? "span" : 'div'
        return (
            <ValidateEditor
                {...this.props}
                onStop={() => this.context.returnFocus()}
                tag={tag}
            />
        )
    }

    focus() {
        ReactDOM.findDOMNode(this).focus();
    }
}
