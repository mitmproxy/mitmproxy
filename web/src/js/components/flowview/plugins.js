var React = require("react");
var _ = require("lodash");

var utils = require("../../utils.js");

var PluginList = [];


var PluginActions = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var sc = flow.server_conn;
        var cc = flow.client_conn;
        var req = flow.request;
        var resp = flow.response;

        var rows = [];
        _.forEach(PluginList, function (plugin) {
            rows.push(<tr>
                        <td>{plugin.title}</td>
                        <td><PluginActionOptions plugin={plugin} flow={flow}/></td>
                      </tr>);
        });

        return (
            <table className="plugins-table">
                <thead>
                    <tr><td>Name</td><td>Options</td></tr>
                </thead>

                <tbody>
                {rows}
                </tbody>
            </table>
        );
    }
});

var Plugins = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;
        return (
            <section>

                <h4>Plugin Actions</h4>

                <PluginActions flow={flow}/>

            </section>
        );
    }
});

module.exports = {'Plugins': Plugins, 'PluginList': PluginList};