import React from "react";
import ReactDOM from 'react-dom';
import _ from "lodash";

import {FlowActions} from "../../actions.js";
import {RequestUtils, isValidHttpVersion, parseUrl, parseHttpVersion} from "../../flow/utils.js";
import {Key, formatTimeStamp} from "../../utils.js";
import ContentView from "./contentview.js";
import {ValueEditor} from "../editor.js";

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
        ReactDOM.findDOMNode(this).focus();
    },
    onKeyDown: function (e) {
        switch (e.keyCode) {
            case Key.BACKSPACE:
                var s = window.getSelection().getRangeAt(0);
                if (s.startOffset === 0 && s.endOffset === 0) {
                    this.props.onRemove(e);
                }
                break;
            case Key.TAB:
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
        var url = RequestUtils.pretty_url(flow.request);
        var httpver = flow.request.http_version;

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
                isValid={isValidHttpVersion}
                inline/>
        </div>
    },
    isValidUrl: function (url) {
        var u = parseUrl(url);
        return !!u.host;
    },
    onMethodChange: function (nextMethod) {
        FlowActions.update(
            this.props.flow,
            {request: {method: nextMethod}}
        );
    },
    onUrlChange: function (nextUrl) {
        var props = parseUrl(nextUrl);
        props.path = props.path || "";
        FlowActions.update(
            this.props.flow,
            {request: props}
        );
    },
    onHttpVersionChange: function (nextVer) {
        var ver = parseHttpVersion(nextVer);
        FlowActions.update(
            this.props.flow,
            {request: {http_version: ver}}
        );
    }
});

var ResponseLine = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var httpver = flow.response.http_version;
        return <div className="first-line response-line">
            <ValueEditor
                ref="httpVersion"
                content={httpver}
                onDone={this.onHttpVersionChange}
                isValid={isValidHttpVersion}
                inline/>
        &nbsp;
            <ValueEditor
                ref="code"
                content={flow.response.status_code + ""}
                onDone={this.onCodeChange}
                isValid={this.isValidCode}
                inline/>
        &nbsp;
            <ValueEditor
                ref="msg"
                content={flow.response.reason}
                onDone={this.onMsgChange}
                inline/>
        </div>;
    },
    isValidCode: function (code) {
        return /^\d+$/.test(code);
    },
    onHttpVersionChange: function (nextVer) {
        var ver = parseHttpVersion(nextVer);
        FlowActions.update(
            this.props.flow,
            {response: {http_version: ver}}
        );
    },
    onMsgChange: function (nextMsg) {
        FlowActions.update(
            this.props.flow,
            {response: {msg: nextMsg}}
        );
    },
    onCodeChange: function (nextCode) {
        nextCode = parseInt(nextCode);
        FlowActions.update(
            this.props.flow,
            {response: {code: nextCode}}
        );
    }
});

export var Request = React.createClass({
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
        FlowActions.update(this.props.flow, {
            request: {
                headers: nextHeaders
            }
        });
    }
});

export var Response = React.createClass({
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
                this.refs.responseLine.refs.status_code.focus();
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
        FlowActions.update(this.props.flow, {
            response: {
                headers: nextHeaders
            }
        });
    }
});

export var Error = React.createClass({
    render: function () {
        var flow = this.props.flow;
        return (
            <section>
                <div className="alert alert-warning">
                {flow.error.msg}
                    <div>
                        <small>{ formatTimeStamp(flow.error.timestamp) }</small>
                    </div>
                </div>
            </section>
        );
    }
});
