import React from "react";
import ReactDOM from 'react-dom';
import {Key} from "../utils.js";

var contentToHtml = function (content) {
    return _.escape(content);
};
var nodeToContent = function (node) {
    return node.textContent;
};

/*
 Basic Editor Functionality
 */
var EditorBase = React.createClass({
    propTypes: {
        content: React.PropTypes.string.isRequired,
        onDone: React.PropTypes.func.isRequired,
        contentToHtml: React.PropTypes.func,
        nodeToContent: React.PropTypes.func, // content === nodeToContent( Node<innerHTML=contentToHtml(content)> )
        onStop: React.PropTypes.func,
        submitOnEnter: React.PropTypes.bool,
        className: React.PropTypes.string,
        tag: React.PropTypes.string
    },
    getDefaultProps: function () {
        return {
            contentToHtml: contentToHtml,
            nodeToContent: nodeToContent,
            submitOnEnter: true,
            className: "",
            tag: "div"
        };
    },
    getInitialState: function () {
        return {
            editable: false
        };
    },
    render: function () {
        var className = "inline-input " + this.props.className;
        var html = {__html: this.props.contentToHtml(this.props.content)};
        var Tag = this.props.tag;
        return <Tag
            {...this.props}
            tabIndex="0"
            className={className}
            contentEditable={this.state.editable || undefined } // workaround: use undef instead of false to remove attr
            onFocus={this.onFocus}
            onMouseDown={this.onMouseDown}
            onClick={this.onClick}
            onBlur={this._stop}
            onKeyDown={this.onKeyDown}
            onInput={this.onInput}
            onPaste={this.onPaste}
            dangerouslySetInnerHTML={html}
        />;
    },
    onPaste: function (e) {
        e.preventDefault();
        var content = e.clipboardData.getData("text/plain");
        document.execCommand("insertHTML", false, content);
    },
    onMouseDown: function (e) {
        this._mouseDown = true;
        window.addEventListener("mouseup", this.onMouseUp);
        this.props.onMouseDown && this.props.onMouseDown(e);
    },
    onMouseUp: function () {
        if (this._mouseDown) {
            this._mouseDown = false;
            window.removeEventListener("mouseup", this.onMouseUp)
        }
    },
    onClick: function (e) {
        this.onMouseUp();
        this.onFocus(e);
    },
    onFocus: function (e) {
        console.log("onFocus", this._mouseDown, this._ignore_events, this.state.editable);
        if (this._mouseDown || this._ignore_events || this.state.editable) {
            return;
        }

        //contenteditable in FireFox is more or less broken.
        // - we need to blur() and then focus(), otherwise the caret is not shown.
        // - blur() + focus() == we need to save the caret position before
        //   Firefox sometimes just doesn't set a caret position => use caretPositionFromPoint
        var sel = window.getSelection();
        var range;
        if (sel.rangeCount > 0) {
            range = sel.getRangeAt(0);
        } else if (document.caretPositionFromPoint && e.clientX && e.clientY) {
            var pos = document.caretPositionFromPoint(e.clientX, e.clientY);
            range = document.createRange();
            range.setStart(pos.offsetNode, pos.offset);
        } else if (document.caretRangeFromPoint && e.clientX && e.clientY) {
            range = document.caretRangeFromPoint(e.clientX, e.clientY);
        } else {
            range = document.createRange();
            range.selectNodeContents(ReactDOM.findDOMNode(this));
        }

        this._ignore_events = true;
        this.setState({editable: true}, function () {
            var node = ReactDOM.findDOMNode(this);
            node.blur();
            node.focus();
            this._ignore_events = false;
            //sel.removeAllRanges();
            //sel.addRange(range);


        });
    },
    stop: function () {
        // a stop would cause a blur as a side-effect.
        // but a blur event must trigger a stop as well.
        // to fix this, make stop = blur and do the actual stop in the onBlur handler.
        ReactDOM.findDOMNode(this).blur();
        this.props.onStop && this.props.onStop();
    },
    _stop: function (e) {
        if (this._ignore_events) {
            return;
        }
        console.log("_stop", _.extend({}, e));
        window.getSelection().removeAllRanges(); //make sure that selection is cleared on blur
        var node = ReactDOM.findDOMNode(this);
        var content = this.props.nodeToContent(node);
        this.setState({editable: false});
        this.props.onDone(content);
        this.props.onBlur && this.props.onBlur(e);
    },
    reset: function () {
        ReactDOM.findDOMNode(this).innerHTML = this.props.contentToHtml(this.props.content);
    },
    onKeyDown: function (e) {
        e.stopPropagation();
        switch (e.keyCode) {
            case Key.ESC:
                e.preventDefault();
                this.reset();
                this.stop();
                break;
            case Key.ENTER:
                if (this.props.submitOnEnter && !e.shiftKey) {
                    e.preventDefault();
                    this.stop();
                }
                break;
            default:
                break;
        }
    },
    onInput: function () {
        var node = ReactDOM.findDOMNode(this);
        var content = this.props.nodeToContent(node);
        this.props.onInput && this.props.onInput(content);
    }
});

/*
 Add Validation to EditorBase
 */
var ValidateEditor = React.createClass({
    propTypes: {
        content: React.PropTypes.string.isRequired,
        onDone: React.PropTypes.func.isRequired,
        onInput: React.PropTypes.func,
        isValid: React.PropTypes.func,
        className: React.PropTypes.string,
    },
    getInitialState: function () {
        return {
            currentContent: this.props.content
        };
    },
    componentWillReceiveProps: function () {
        this.setState({currentContent: this.props.content});
    },
    onInput: function (content) {
        this.setState({currentContent: content});
        this.props.onInput && this.props.onInput(content);
    },
    render: function () {
        var className = this.props.className || "";
        if (this.props.isValid) {
            if (this.props.isValid(this.state.currentContent)) {
                className += " has-success";
            } else {
                className += " has-warning"
            }
        }
        return <EditorBase
            {...this.props}
            ref="editor"
            className={className}
            onDone={this.onDone}
            onInput={this.onInput}
        />;
    },
    onDone: function (content) {
        if (this.props.isValid && !this.props.isValid(content)) {
            this.refs.editor.reset();
            content = this.props.content;
        }
        this.props.onDone(content);
    }
});

/*
 Text Editor with mitmweb-specific convenience features
 */
export var ValueEditor = React.createClass({
    contextTypes: {
        returnFocus: React.PropTypes.func
    },
    propTypes: {
        content: React.PropTypes.string.isRequired,
        onDone: React.PropTypes.func.isRequired,
        inline: React.PropTypes.bool,
    },
    render: function () {
        var tag = this.props.inline ? "span" : "div";
        return <ValidateEditor
            {...this.props}
            onStop={this.onStop}
            tag={tag}
        />;
    },
    focus: function () {
        ReactDOM.findDOMNode(this).focus();
    },
    onStop: function () {
        this.context.returnFocus();
    }
});