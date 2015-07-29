var React = require("react");
var _ = require("lodash");

var utils = require("../../utils.js");

var PluginList = [];

var PluginAction = React.createClass({
    triggerClick: function (event) {
        var flow = this.props.flow;
        console.log(flow);
        var el = event.target;
        $.ajax({
            type: "POST",
            url: "/flows/" + flow.id + "/plugins/" + this.props.plugin.id,
            contentType: 'application/json',
            data: JSON.stringify(_.find(this.props.plugin.actions, function(o){return (o.id === el.getAttribute('id'))}))
        });
    },

    render: function () {
        var plugin = this.props.plugin; 

        var ret = [];
        _.forEach(plugin.actions, function (action) {
            ret.push(<div><input type="button" id={action.id} data-action={action.action} onClick={this.triggerClick} value={action.title}/></div>);
        }.bind(this));

        return (<span>{ret}</span>);
    }
});


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
                        <td><PluginAction plugin={plugin} flow={flow}/></td>
                      </tr>);
        });

        return (
            <table className="plugins-table">
                <thead>
                    <tr><td>Name</td><td>Actions</td></tr>
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

module.exports = {'Plugins': Plugins, 'PluginList': PluginList, 'PluginActions': PluginActions};