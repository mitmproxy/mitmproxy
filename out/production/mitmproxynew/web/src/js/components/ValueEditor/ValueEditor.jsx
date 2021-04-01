import React, { Component } from 'react'
import PropTypes from 'prop-types'
import _ from "lodash"
import classnames from 'classnames'

import { Key } from '../../utils'

export default class ValueEditor extends Component {

    static propTypes = {
        content: PropTypes.string.isRequired,
        readonly: PropTypes.bool,
        onDone: PropTypes.func.isRequired,
        className: PropTypes.string,
        onInput: PropTypes.func,
        onKeyDown: PropTypes.func,
    }

    static defaultProps = {
        onInput: () => {},
        onKeyDown: () => {},
    }

    constructor(props) {
        super(props)
        this.state = { editable: false }

        this.onPaste = this.onPaste.bind(this)
        this.onMouseDown = this.onMouseDown.bind(this)
        this.onMouseUp = this.onMouseUp.bind(this)
        this.onFocus = this.onFocus.bind(this)
        this.onClick = this.onClick.bind(this)
        this.blur = this.blur.bind(this)
        this.onBlur = this.onBlur.bind(this)
        this.reset = this.reset.bind(this)
        this.onKeyDown = this.onKeyDown.bind(this)
        this.onInput = this.onInput.bind(this)
    }

    blur() {
        // a stop would cause a blur as a side-effect.
        // but a blur event must trigger a stop as well.
        // to fix this, make stop = blur and do the actual stop in the onBlur handler.
        this.input.blur()
    }

    reset() {
        this.input.innerHTML = _.escape(this.props.content)
    }

    render() {
        let className = classnames(
            'inline-input',
            {
                'readonly': this.props.readonly,
                'editable': !this.props.readonly
            },
            this.props.className
        )
        return (
            <div
                ref={input => this.input = input}
                tabIndex={this.props.readonly ? undefined : 0}
                className={className}
                contentEditable={this.state.editable || undefined}
                onFocus={this.onFocus}
                onMouseDown={this.onMouseDown}
                onClick={this.onClick}
                onBlur={this.onBlur}
                onKeyDown={this.onKeyDown}
                onInput={this.onInput}
                onPaste={this.onPaste}
                dangerouslySetInnerHTML={{ __html: _.escape(this.props.content) }}
            ></div>
        )
    }

    onPaste(e) {
        e.preventDefault()
        var content = e.clipboardData.getData('text/plain')
        document.execCommand('insertHTML', false, content)
    }

    onMouseDown(e) {
        this._mouseDown = true
        window.addEventListener('mouseup', this.onMouseUp)
    }

    onMouseUp() {
        if (this._mouseDown) {
            this._mouseDown = false
            window.removeEventListener('mouseup', this.onMouseUp)
        }
    }

    onClick(e) {
        this.onMouseUp()
        this.onFocus(e)
    }

    onFocus(e) {
        if (this._mouseDown || this._ignore_events || this.state.editable || this.props.readonly) {
            return
        }

        // contenteditable in FireFox is more or less broken.
        // - we need to blur() and then focus(), otherwise the caret is not shown.
        // - blur() + focus() == we need to save the caret position before
        //   Firefox sometimes just doesn't set a caret position => use caretPositionFromPoint
        const sel = window.getSelection()
        let range
        if (sel.rangeCount > 0) {
            range = sel.getRangeAt(0)
        } else if (document.caretPositionFromPoint && e.clientX && e.clientY) {
            const pos = document.caretPositionFromPoint(e.clientX, e.clientY)
            range = document.createRange()
            range.setStart(pos.offsetNode, pos.offset)
        } else if (document.caretRangeFromPoint && e.clientX && e.clientY) {
            range = document.caretRangeFromPoint(e.clientX, e.clientY)
        } else {
            range = document.createRange()
            range.selectNodeContents(this.input)
        }

        this._ignore_events = true
        this.setState({ editable: true }, () => {
            this.input.blur()
            this.input.focus()
            this._ignore_events = false
            range.selectNodeContents(this.input)
            sel.removeAllRanges();
            sel.addRange(range);
        })
    }

    onBlur(e) {
        if (this._ignore_events || this.props.readonly) {
            return
        }
        window.getSelection().removeAllRanges() //make sure that selection is cleared on blur
        this.setState({ editable: false })
        this.props.onDone(this.input.textContent)
    }


    onKeyDown(e) {
        e.stopPropagation()
        switch (e.keyCode) {
            case Key.ESC:
                e.preventDefault()
                this.reset()
                this.blur()
                break
            case Key.ENTER:
                if (!e.shiftKey) {
                    e.preventDefault()
                    this.blur()
                }
                break
            default:
                break
        }
        this.props.onKeyDown(e)
    }

    onInput() {
        this.props.onInput(this.input.textContent)
    }
}
