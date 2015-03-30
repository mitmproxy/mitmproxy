var React = require("react");
var _ = require("lodash");

var common = require("../common.js");
var actions = require("../../actions.js");
var flowutils = require("../../flow/utils.js");
var utils = require("../../utils.js");
var ContentView = require("./contentview.js");

var Headers = React.createClass({
    propTypes: {
        onChange: React.PropTypes.func.isRequired,
        message: React.PropTypes.object.isRequired
    },
    onChange: function (row, col, val) {
        var nextHeaders = _.cloneDeep(this.props.message.headers);
        nextHeaders[row][col] = val;
        if (!nextHeaders[row][0] && !nextHeaders[row][1]) {
            // do not delete last row
            if (nextHeaders.length === 1) {
                nextHeaders[0][0] = "Name";
                nextHeaders[0][1] = "Value";
            } else {
                nextHeaders.splice(row, 1);
                // manually move selection target if this has been the last row.
                if (row === nextHeaders.length) {
                    this._nextSel = (row - 1) + "-value";
                }
            }
        }
        this.props.onChange(nextHeaders);
    },
    edit: function () {
        this.refs["0-key"].focus();
    },
    onTab: function (row, col, e) {
        var headers = this.props.message.headers;
        if (row === headers.length - 1 && col === 1) {
            e.preventDefault();

            var nextHeaders = _.cloneDeep(this.props.message.headers);
            nextHeaders.push(["Name", "Value"]);
            this.props.onChange(nextHeaders);
            this._nextSel = (row + 1) + "-key";
        }
    },
    componentDidUpdate: function () {
        if (this._nextSel && this.refs[this._nextSel]) {
            this.refs[this._nextSel].focus();
            this._nextSel = undefined;
        }
    },
    onRemove: function (row, col, e) {
        if (col === 1) {
            e.preventDefault();
            this.refs[row + "-key"].focus();
        } else if (row > 0) {
            e.preventDefault();
            this.refs[(row - 1) + "-value"].focus();
        }
    },
    render: function () {

        var rows = this.props.message.headers.map(function (header, i) {

            var kEdit = <HeaderInlineInput
                ref={i + "-key"}
                content={header[0]}
                onChange={this.onChange.bind(null, i, 0)}
                onRemove={this.onRemove.bind(null, i, 0)}
                onTab={this.onTab.bind(null, i, 0)}/>;
            var vEdit = <HeaderInlineInput
                ref={i + "-value"}
                content={header[1]}
                onChange={this.onChange.bind(null, i, 1)}
                onRemove={this.onRemove.bind(null, i, 1)}
                onTab={this.onTab.bind(null, i, 1)}/>;
            return (
                <tr key={i}>
                    <td className="header-name">{kEdit}:</td>
                    <td className="header-value">{vEdit}</td>
                </tr>
            );
        }.bind(this));
        return (
            <table className="header-table">
                <tbody>
                    {rows}
                </tbody>
            </table>
        );
    }
});


var InlineInput = React.createClass({
    mixins: [common.ChildFocus],
    propTypes: {
        content: React.PropTypes.string.isRequired, //must be string to match strict equality.
        onChange: React.PropTypes.func.isRequired,
    },
    getInitialState: function () {
        return {
            editable: false
        };
    },
    render: function () {
        var Tag = this.props.tag || "span";
        var className = "inline-input " + (this.props.className || "");
        var html = {__html: _.escape(this.props.content)};
        return <Tag
            {...this.props}
            tabIndex="0"
            className={className}
            contentEditable={this.state.editable || undefined}
            onInput={this.onInput}
            onFocus={this.onFocus}
            onBlur={this.onBlur}
            onKeyDown={this.onKeyDown}
            dangerouslySetInnerHTML={html}
        />;
    },
    onKeyDown: function (e) {
        e.stopPropagation();
        switch (e.keyCode) {
            case utils.Key.ESC:
                this.blur();
                break;
            case utils.Key.ENTER:
                e.preventDefault();
                if (!e.ctrlKey) {
                    this.blur();
                } else {
                    this.props.onDone && this.props.onDone();
                }
                break;
            default:
                this.props.onKeyDown && this.props.onKeyDown(e);
                break;
        }
    },
    blur: function () {
        this.getDOMNode().blur();
        window.getSelection().removeAllRanges();
        this.context.returnFocus && this.context.returnFocus();
    },
    focus: function () {
        React.findDOMNode(this).focus();
        var range = document.createRange();
        range.selectNodeContents(this.getDOMNode());
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    },
    onFocus: function () {
        this.setState({editable: true}, this.focus);
    },
    onBlur: function (e) {
        this.setState({editable: false});
        this.handleChange();
        this.props.onDone && this.props.onDone();
    },
    onInput: function () {
        this.handleChange();
    },
    handleChange: function () {
        var content = this.getDOMNode().textContent;
        if (content !== this.props.content) {
            this.props.onChange(content);
        }
    }
});

var HeaderInlineInput = React.createClass({
    render: function () {
        return <InlineInput ref="input" {...this.props} onKeyDown={this.onKeyDown}/>;
    },
    focus: function () {
        this.getDOMNode().focus();
    },
    onKeyDown: function (e) {
        switch (e.keyCode) {
            case utils.Key.BACKSPACE:
                var s = window.getSelection().getRangeAt(0);
                if (s.startOffset === 0 && s.endOffset === 0) {
                    this.props.onRemove(e);
                }
                break;
            case utils.Key.TAB:
                if (!e.shiftKey) {
                    this.props.onTab(e);
                }
                break;
        }
    }
});

var ValidateInlineInput = React.createClass({
    propTypes: {
        onChange: React.PropTypes.func.isRequired,
        isValid: React.PropTypes.func.isRequired,
        immediate: React.PropTypes.bool
    },
    getInitialState: function () {
        return {
            content: this.props.content,
            originalContent: this.props.content
        };
    },
    focus: function () {
        this.getDOMNode().focus();
    },
    onChange: function (val) {
        this.setState({
            content: val
        });
        if (this.props.immediate && val !== this.state.originalContent && this.props.isValid(val)) {
            this.props.onChange(val);
        }
    },
    onDone: function () {
        if (this.state.content === this.state.originalContent) {
            return true;
        }
        if (this.props.isValid(this.state.content)) {
            this.props.onChange(this.state.content);
        } else {
            this.setState({
                content: this.state.originalContent
            });
        }
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.content !== this.state.content) {
            this.setState({
                content: nextProps.content,
                originalContent: nextProps.content
            })
        }
    },
    render: function () {
        var className = this.props.className || "";
        if (this.props.isValid(this.state.content)) {
            className += " has-success";
        } else {
            className += " has-warning"
        }
        return <InlineInput {...this.props}
            className={className}
            content={this.state.content}
            onChange={this.onChange}
            onDone={this.onDone}
        />;
    }
});

var RequestLine = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var url = flowutils.RequestUtils.pretty_url(flow.request);
        var httpver = "HTTP/" + flow.request.httpversion.join(".");

        return <div className="first-line request-line">
            <InlineInput ref="method" content={flow.request.method} onChange={this.onMethodChange}/>
        &nbsp;
            <ValidateInlineInput ref="url" content={url} onChange={this.onUrlChange} isValid={this.isValidUrl} />
        &nbsp;
            <ValidateInlineInput ref="httpVersion" immediate content={httpver} onChange={this.onHttpVersionChange} isValid={flowutils.isValidHttpVersion} />
        </div>
    },
    isValidUrl: function (url) {
        var u = flowutils.parseUrl(url);
        return !!u.host;
    },
    onMethodChange: function (nextMethod) {
        actions.FlowActions.update(
            this.props.flow,
            {request: {method: nextMethod}}
        );
    },
    onUrlChange: function (nextUrl) {
        var props = flowutils.parseUrl(nextUrl);
        props.path = props.path || "";
        actions.FlowActions.update(
            this.props.flow,
            {request: props}
        );
    },
    onHttpVersionChange: function (nextVer) {
        var ver = flowutils.parseHttpVersion(nextVer);
        actions.FlowActions.update(
            this.props.flow,
            {request: {httpversion: ver}}
        );
    }
});

var ResponseLine = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var httpver = "HTTP/" + flow.response.httpversion.join(".");
        return <div className="first-line response-line">
            <ValidateInlineInput ref="httpVersion" immediate content={httpver} onChange={this.onHttpVersionChange} isValid={flowutils.isValidHttpVersion} />
        &nbsp;
            <ValidateInlineInput ref="code" immediate content={flow.response.code + ""} onChange={this.onCodeChange} isValid={this.isValidCode} />
        &nbsp;
            <InlineInput ref="msg" content={flow.response.msg} onChange={this.onMsgChange}/>

        </div>;
    },
    isValidCode: function (code) {
        return /^\d+$/.test(code);
    },
    onHttpVersionChange: function (nextVer) {
        var ver = flowutils.parseHttpVersion(nextVer);
        actions.FlowActions.update(
            this.props.flow,
            {response: {httpversion: ver}}
        );
    },
    onMsgChange: function (nextMsg) {
        actions.FlowActions.update(
            this.props.flow,
            {response: {msg: nextMsg}}
        );
    },
    onCodeChange: function (nextCode) {
        nextCode = parseInt(nextCode);
        actions.FlowActions.update(
            this.props.flow,
            {response: {code: nextCode}}
        );
    }
});

var Request = React.createClass({
    render: function () {
        var flow = this.props.flow;
        return (
            <section className="request">
                <RequestLine ref="requestLine" flow={flow}/>
                {/*<ResponseLine flow={flow}/>*/}
                <Headers ref="headers" message={flow.request} onChange={this.onHeaderChange}/>
                <hr/>
                <ContentView flow={flow} message={flow.request}/>
            </section>
        );
    },
    edit: function (k) {
        switch (k) {
            case "m":
                this.refs.requestLine.refs.method.focus();
                break;
            case "u":
                this.refs.requestLine.refs.url.focus();
                break;
            case "v":
                this.refs.requestLine.refs.httpVersion.focus();
                break;
            case "h":
                this.refs.headers.edit();
                break;
            default:
                throw "Unimplemented: "+ k;
        }
    },
    onHeaderChange: function (nextHeaders) {
        actions.FlowActions.update(this.props.flow, {
            request: {
                headers: nextHeaders
            }
        });
    }
});

var Response = React.createClass({
    render: function () {
        var flow = this.props.flow;
        return (
            <section className="response">
                {/*<RequestLine flow={flow}/>*/}
                <ResponseLine ref="responseLine" flow={flow}/>
                <Headers ref="headers" message={flow.response} onChange={this.onHeaderChange}/>
                <hr/>
                <ContentView flow={flow} message={flow.response}/>
            </section>
        );
    },
    edit: function (k) {
        switch (k) {
            case "c":
                this.refs.responseLine.refs.code.focus();
                break;
            case "m":
                this.refs.responseLine.refs.msg.focus();
                break;
            case "v":
                this.refs.responseLine.refs.httpVersion.focus();
                break;
            case "h":
                this.refs.headers.edit();
                break;
            default:
                throw "Unimplemented: "+ k;
        }
    },
    onHeaderChange: function (nextHeaders) {
        actions.FlowActions.update(this.props.flow, {
            response: {
                headers: nextHeaders
            }
        });
    }
});

var Error = React.createClass({
    render: function () {
        var flow = this.props.flow;
        return (
            <section>
                <div className="alert alert-warning">
                {flow.error.msg}
                    <div>
                        <small>{ utils.formatTimeStamp(flow.error.timestamp) }</small>
                    </div>
                </div>
            </section>
        );
    }
});

module.exports = {
    Request: Request,
    Response: Response,
    Error: Error
};