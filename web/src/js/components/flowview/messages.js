var React = require("react");

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

var Request = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            flow.request.method,
            flowutils.RequestUtils.pretty_url(flow.request),
            "HTTP/" + flow.request.httpversion.join(".")
        ].join(" ");

        //TODO: Styling

        return (
            <section>
                <div className="first-line">{ first_line }</div>
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
        var first_line = [
            "HTTP/" + flow.response.httpversion.join("."),
            flow.response.code,
            flow.response.msg
        ].join(" ");

        //TODO: Styling

        return (
            <section>
                <div className="first-line">{ first_line }</div>
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