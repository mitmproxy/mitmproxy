import React, { Component, PropTypes } from 'react'
import ReactDOM from 'react-dom'
import {Key} from '../../utils.js'

export default class EditorBase extends Component {

    static propTypes = {
        content: PropTypes.string.isRequired,
        onDone: PropTypes.func.isRequired,
        contentToHtml: PropTypes.func,
        nodeToContent: PropTypes.func,
        onStop: PropTypes.func,
        submitOnEnter: PropTypes.bool,
        className: PropTypes.string,
        tag: PropTypes.string,
    }

    static defaultProps = {
        contentToHtml: content => _.escape(content),
        nodeToContent: node => node.textContent,
        submitOnEnter: true,
        className: '',
        tag: 'div',
        onStop: _.noop,
        onMouseDown: _.noop,
        onBlur: _.noop,
        onInput: _.noop,
    }

    constructor(props) {
        super(props)
        this.state = {editable: false}

        this.onPaste = this.onPaste.bind(this)
        this.onMouseDown = this.onMouseDown.bind(this)
        this.onMouseUp = this.onMouseUp.bind(this)
        this.onFocus = this.onFocus.bind(this)
        this.onClick = this.onClick.bind(this)
        this.stop = this.stop.bind(this)
        this.onBlur = this.onBlur.bind(this)
        this.reset = this.reset.bind(this)
        this.onKeyDown = this.onKeyDown.bind(this)
        this.onInput = this.onInput.bind(this)
    }

    stop() {
        // a stop would cause a blur as a side-effect.
        // but a blur event must trigger a stop as well.
        // to fix this, make stop = blur and do the actual stop in the onBlur handler.
        ReactDOM.findDOMNode(this).blur()
        this.props.onStop()
    }

    render() {
        return (
            <this.props.tag
                {...this.props}
                tabIndex="0"
                className={`inline-input ${this.props.className}`}
                contentEditable={this.state.editable || undefined}
                onFocus={this.onFocus}
                onMouseDown={this.onMouseDown}
                onClick={this.onClick}
                onBlur={this.onBlur}
                onKeyDown={this.onKeyDown}
                onInput={this.onInput}
                onPaste={this.onPaste}
                dangerouslySetInnerHTML={{ __html: this.props.contentToHtml(this.props.content) }}
            />
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
        this.props.onMouseDown(e)
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
        if (this._mouseDown || this._ignore_events || this.state.editable) {
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
            range.selectNodeContents(ReactDOM.findDOMNode(this))
        }

        this._ignore_events = true
        this.setState({ editable: true }, () => {
            const node = ReactDOM.findDOMNode(this)
            node.blur()
            node.focus()
            this._ignore_events = false
        })
    }

    onBlur(e) {
        if (this._ignore_events) {
            return
        }
        window.getSelection().removeAllRanges() //make sure that selection is cleared on blur
        this.setState({ editable: false })
        this.props.onDone(this.props.nodeToContent(ReactDOM.findDOMNode(this)))
        this.props.onBlur(e)
    }

    reset() {
        ReactDOM.findDOMNode(this).innerHTML = this.props.contentToHtml(this.props.content)
    }

    onKeyDown(e) {
        e.stopPropagation()
        switch (e.keyCode) {
            case Key.ESC:
                e.preventDefault()
                this.reset()
                this.stop()
                break
            case Key.ENTER:
                if (this.props.submitOnEnter && !e.shiftKey) {
                    e.preventDefault()
                    this.stop()
                }
                break
            default:
                break
        }
    }

    onInput() {
        this.props.onInput(this.props.nodeToContent(ReactDOM.findDOMNode(this)))
    }
}
