var React = require("react");
var _ = require("lodash");

var common = require("../common.js");
var actions = require("../../actions.js");
var flowutils = require("../../flow/utils.js");
var utils = require("../../utils.js");
var ContentView = require("./contentview.js");

var Headers = React.createClass({
    render: function () {
        var rows = this.props.message.headers.map(function (header, i) {
            return (
                <tr key={i}>
                    <td className="header-name">{header[0] + ":"}</td>
                    <td className="header-value">{header[1]}</td>
                </tr>
            );
        });
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
                break;
        }
    },
    blur: function(){
        this.getDOMNode().blur();
        this.context.returnFocus && this.context.returnFocus();
    },
    selectContents: function () {
        var range = document.createRange();
        range.selectNodeContents(this.getDOMNode());
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    },
    onFocus: function () {
        this.setState({editable: true}, this.selectContents);
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

var ValidateInlineInput = React.createClass({
    getInitialState: function () {
        return {
            content: ""+this.props.content,
            originalContent: ""+this.props.content
        };
    },
    onChange: function (val) {
        this.setState({
            content: val
        });
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
                content: ""+nextProps.content,
                originalContent: ""+nextProps.content
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
            <ValidateInlineInput content={flow.request.method} onChange={this.onMethodChange} isValid={this.isValidMethod}/>
        &nbsp;
            <ValidateInlineInput content={url} onChange={this.onUrlChange} isValid={this.isValidUrl} />
        &nbsp;
            <ValidateInlineInput content={httpver} onChange={this.onHttpVersionChange} isValid={flowutils.isValidHttpVersion} />
        </div>
    },
    isValidMethod: function (method) {
        return true;
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
            <ValidateInlineInput content={httpver} onChange={this.onHttpVersionChange} isValid={flowutils.isValidHttpVersion} />
        &nbsp;
            <ValidateInlineInput content={flow.response.code} onChange={this.onCodeChange} isValid={this.isValidCode} />
        &nbsp;
            <ValidateInlineInput content={flow.response.msg} onChange={this.onMsgChange} isValid={this.isValidMsg} />

        </div>;
    },
    isValidCode: function (code) {
        return /^\d+$/.test(code);
    },
    isValidMsg: function () {
        return true;
    },
    onHttpVersionChange: function (nextVer) {
        var ver = flowutils.parseHttpVersion(nextVer);
        actions.FlowActions.update(
            this.props.flow,
            {response: {httpversion: ver}}
        );
    },
    onMsgChange: function(nextMsg){
        actions.FlowActions.update(
            this.props.flow,
            {response: {msg: nextMsg}}
        );
    },
    onCodeChange: function(nextCode){
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
                <RequestLine flow={flow}/>
                {/*<ResponseLine flow={flow}/>*/}
                <Headers message={flow.request}/>
                <hr/>
                <ContentView flow={flow} message={flow.request}/>
            </section>
        );
    }
});

var Response = React.createClass({
    render: function () {
        var flow = this.props.flow;
        return (
            <section className="response">
                {/*<RequestLine flow={flow}/>*/}
                <ResponseLine flow={flow}/>
                <Headers message={flow.response}/>
                <hr/>
                <ContentView flow={flow} message={flow.response}/>
            </section>
        );
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