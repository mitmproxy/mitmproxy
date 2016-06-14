import React, { Component, PropTypes } from 'react'
import ReactDOM from 'react-dom'
import EditorBase from './EditorBase'

export default class ValidateEditor extends Component {

    static propTypes = {
        content: PropTypes.string.isRequired,
        onDone: PropTypes.func.isRequired,
        onInput: PropTypes.func,
        isValid: PropTypes.func,
        className: PropTypes.string,
    }

    constructor(props) {
        super(props)
        this.state = { currentContent: props.content }
        this.onInput = this.onInput.bind(this)
        this.onDone = this.onDone.bind(this)
    }

    componentWillReceiveProps(nextProps) {
        this.setState({ currentContent: nextProps.content })
    }

    onInput(currentContent) {
        this.setState({ currentContent })
        this.props.onInput && this.props.onInput(currentContent)
    }

    onDone(content) {
        if (this.props.isValid && !this.props.isValid(content)) {
            this.refs.editor.reset()
            content = this.props.content
        }
        this.props.onDone(content)
    }

    render() {
        let className = this.props.className || ''
        if (this.props.isValid) {
            if (this.props.isValid(this.state.currentContent)) {
                className += ' has-success'
            } else {
                className += ' has-warning'
            }
        }
        return (
            <EditorBase
                {...this.props}
                ref="editor"
                className={className}
                onDone={this.onDone}
                onInput={this.onInput}
            />
        )
    }
}
