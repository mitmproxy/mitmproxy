var React = require("react");

var flowutils = require("../../flow/utils.js");
var utils = require("../../utils.js");

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

var Request = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            flow.request.method,
            flowutils.RequestUtils.pretty_url(flow.request),
            "HTTP/" + flow.request.httpversion.join(".")
        ].join(" ");
        var content = null;
        if (flow.request.contentLength > 0) {
            content = "Request Content Size: " + utils.formatSize(flow.request.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <div className="first-line">{ first_line }</div>
                <Headers message={flow.request}/>
                <hr/>
                {content}
            </section>
        );
    }
});

var Response = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            "HTTP/" + flow.response.httpversion.join("."),
            flow.response.code,
            flow.response.msg
        ].join(" ");
        var content = null;
        if (flow.response.contentLength > 0) {
            content = "Response Content Size: " + utils.formatSize(flow.response.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <div className="first-line">{ first_line }</div>
                <Headers message={flow.response}/>
                <hr/>
                {content}
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