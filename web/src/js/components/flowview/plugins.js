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
            data: JSON.stringify(_.find(this.props.plugin.actions, function(o){return ('action-' + o.id === el.getAttribute('id'))}))
        });
    },

    render: function () {
        var plugin = this.props.plugin; 

        var ret = [];
        _.forEach(plugin.actions, function (action) {
            ret.push(<div><input type="button" id={'action-' + action.id} data-action={action.action} onClick={this.triggerClick} value={action.title}/></div>);
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

var PluginOption = React.createClass({
    triggerChange: function() {
        $.ajax({
            type: "POST",
            url: "/plugins/" + this.props.plugin.id + "/options/" + this.props.option.id,
            contentType: 'application/json',
            data: JSON.stringify({'every_flow': !this.state.every_flow})
        }).done(function(data){
            if (data.data.success)
                this.setState({every_flow: !this.state.every_flow});
            else
                console.log("Something went wrong trying to change option");
        }.bind(this));
    },

    getInitialState: function () {
        return {every_flow: this.props.initial_every_flow};
    },

    render: function () {
        var option = this.props.option;
        return (
            <div>
                <label for={option.id}>{option.title}s</label>
                <input type="checkbox"
                       id={'option-' + option.id}
                       data-action={option.action}
                       onChange={this.triggerChange}
                       checked={this.state.every_flow}/>
            </div>);
    }
});

var PluginOptionList = React.createClass({
    render: function () {
        var plugin = this.props.plugin; 

        var ret = [];
        _.forEach(plugin.actions, function (action) {
            ret.push(<PluginOption option={action} plugin={plugin} initial_every_flow={action.state.every_flow}/>);
        }.bind(this));

        return (<span>{ret}</span>);
    }
});

var PluginOptionsPane = React.createClass({
    getInitialState: function() {
        return { plugins: PluginList };
    },

    render: function () {

        var rows = [];
        // there's a race condition here if the page is loaded w/ url
        // /plugins. will result in empty options list, we should probably
        // have the pluginList somewhere in state so it can trigger re-render
        console.log("plugin list...");
        console.log(PluginList);
        _.forEach(PluginList, function (plugin) {
            rows.push(<tr>
                        <td>{plugin.title}</td>
                        <td><PluginOptionList plugin={plugin}/></td>
                      </tr>);
        });

        return (
            <table className="plugins-table">
                <thead>
                    <tr><td>Name</td><td>Run Action on Every Flow</td></tr>
                </thead>

                <tbody>
                {rows}
                </tbody>
            </table>
        );
    }
});

var PluginsTopLevel = React.createClass({
    render: function () {
        return (<div><section><PluginOptionsPane/></section></div>);
    }
});

var PluginsFlowLevel = React.createClass({
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

module.exports = {
    'PluginsFlowLevel': PluginsFlowLevel,
    'PluginList': PluginList,
    'PluginActions': PluginActions,
    'PluginsTopLevel': PluginsTopLevel
};