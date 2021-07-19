import React, { Component } from 'react'
import ValueEditor from './ValueEditor'
import classnames from 'classnames'

type ValidateEditorProps = {
    content: string | undefined,
    readonly: boolean,
    onDone: (content: string) => void,
    className?: string,
    isValid: (content: string) => boolean,
}

type ValidateEditorStates = {
    valid: boolean,
}

export default class ValidateEditor extends Component<ValidateEditorProps, ValidateEditorStates> {
    constructor(props) {
        super(props)
        this.state = { valid: props.isValid(props.content) }
        this.onInput = this.onInput.bind(this)
        this.onDone = this.onDone.bind(this)
    }

    UNSAFE_componentWillReceiveProps(nextProps) {
        this.setState({ valid: nextProps.isValid(nextProps.content) })
    }

    onInput(content) {
        this.setState({ valid: this.props.isValid(content) })
    }

    onDone(content) {
        if (!this.props.isValid(content)) {
            this.editor.reset()
            content = this.props.content
        }
        this.props.onDone(content)
    }

    render() {
        let className = classnames(
            this.props.className,
            {
                'has-success': this.state.valid,
                'has-warning': !this.state.valid
            }
        )
        return (
            <ValueEditor
                content={this.props.content}
                readonly={this.props.readonly}
                onDone={this.onDone}
                onInput={this.onInput}
                className={className}
                ref={(e) => this.editor = e}
            />
        )
    }
}
