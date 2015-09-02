var React = require("react");
var _ = require("lodash");

var common = require("../common.js");
var actions = require("../../actions.js");
var flowutils = require("../../flow/utils.js");
var utils = require("../../utils.js");
var ContentView = require("./contentview.js").ContentView;
var ValueEditor = require("../editor.js").ValueEditor;

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

            var kEdit = <HeaderEditor
                ref={i + "-key"}
                content={header[0]}
                onDone={this.onChange.bind(null, i, 0)}
                onRemove={this.onRemove.bind(null, i, 0)}
                onTab={this.onTab.bind(null, i, 0)}/>;
            var vEdit = <HeaderEditor
                ref={i + "-value"}
                content={header[1]}
                onDone={this.onChange.bind(null, i, 1)}
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

var HeaderEditor = React.createClass({
    render: function () {
        return <ValueEditor ref="input" {...this.props} onKeyDown={this.onKeyDown} inline/>;
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

var RequestLine = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var url = flowutils.RequestUtils.pretty_url(flow.request);
        var httpver = "HTTP/" + flow.request.httpversion.join(".");

        return <div className="first-line request-line">
            <ValueEditor
                ref="method"
                content={flow.request.method}
                onDone={this.onMethodChange}
                inline/>
        &nbsp;
            <ValueEditor
                ref="url"
                content={url}
                onDone={this.onUrlChange}
                isValid={this.isValidUrl}
                inline/>
        &nbsp;
            <ValueEditor
                ref="httpVersion"
                content={httpver}
                onDone={this.onHttpVersionChange}
                isValid={flowutils.isValidHttpVersion}
                inline/>
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
            <ValueEditor
                ref="httpVersion"
                content={httpver}
                onDone={this.onHttpVersionChange}
                isValid={flowutils.isValidHttpVersion}
                inline/>
        &nbsp;
            <ValueEditor
                ref="code"
                content={flow.response.code + ""}
                onDone={this.onCodeChange}
                isValid={this.isValidCode}
                inline/>
        &nbsp;
            <ValueEditor
                ref="msg"
                content={flow.response.msg}
                onDone={this.onMsgChange}
                inline/>
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
    contextTypes: {
        pluginStore: React.PropTypes.array.isRequired
    },
    childContextTypes: {
        pluginStore: React.PropTypes.array.isRequired
    },
    getChildContext: function () {
        return {pluginStore: this.context.pluginStore};
    },
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
                throw "Unimplemented: " + k;
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
                throw "Unimplemented: " + k;
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