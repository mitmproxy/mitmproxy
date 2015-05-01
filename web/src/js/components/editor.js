var React = require("react");
var common = require("./common.js");
var utils = require("../utils.js");

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
            onBlur={this._stop}
            onKeyDown={this.onKeyDown}
            onInput={this.onInput}
            dangerouslySetInnerHTML={html}
        />;
    },
    onFocus: function (e) {
        this.setState({editable: true}, function () {
            React.findDOMNode(this).focus();
            var range = document.createRange();
            range.selectNodeContents(this.getDOMNode());
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        });
        this.props.onFocus && this.props.onFocus(e);
    },
    stop: function () {
        // a stop would cause a blur as a side-effect.
        // but a blur event must trigger a stop as well.
        // to fix this, make stop = blur and do the actual stop in the onBlur handler.
        React.findDOMNode(this).blur();
    },
    _stop: function (e) {
        window.getSelection().removeAllRanges(); //make sure that selection is cleared on blur
        var node = React.findDOMNode(this);
        var content = this.props.nodeToContent(node);
        this.setState({editable: false});
        this.props.onDone(content);
        this.props.onBlur && this.props.onBlur(e);
    },
    cancel: function () {
        React.findDOMNode(this).innerHTML = this.props.contentToHtml(this.props.content);
        this.stop();
    },
    onKeyDown: function (e) {
        e.stopPropagation();
        switch (e.keyCode) {
            case utils.Key.ESC:
                e.preventDefault();
                this.cancel();
                break;
            case utils.Key.ENTER:
                if (this.props.submitOnEnter) {
                    e.preventDefault();
                    this.stop();
                }
                break;
            default:
                break;
        }
    },
    onInput: function () {
        var node = React.findDOMNode(this);
        var content = this.props.nodeToContent(node);
        node.innerHTML = this.props.contentToHtml(content);
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
    getInitialState: function(){
        return {
            currentContent: this.props.content
        };
    },
    componentWillReceiveProps: function(){
        this.setState({currentContent: this.props.content});
    },
    onInput: function(content){
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
        if(this.props.isValid && !this.props.isValid(content)){
            this.refs.editor.cancel();
            content = this.props.content;
        }
        this.props.onDone(content);
    }
});

/*
Text Editor with mitmweb-specific convenience features
 */
var ValueEditor = React.createClass({
    mixins: [common.ChildFocus],
    propTypes: {
        content: React.PropTypes.string.isRequired,
        onDone: React.PropTypes.func.isRequired,
        inline: React.PropTypes.bool,
    },
    render: function () {
        var tag = this.props.inline ? "span" : "div";
        return <ValidateEditor
            {...this.props}
            onBlur={this.onBlur}
            tag={tag}
        />;
    },
    focus: function () {
        React.findDOMNode(this).focus();
    },
    onBlur: function(e){
        if(!e.relatedTarget){
            this.returnFocus();
        }
        this.props.onBlur && this.props.onBlur(e);
    }
});

module.exports = {
    ValueEditor: ValueEditor
};