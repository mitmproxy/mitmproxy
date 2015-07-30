var React = require("react");
var _ = require("lodash");

var utils = require("../../utils.js");
var MessageUtils = require("../../flow/utils.js").MessageUtils;

var PluginAction = React.createClass({
    triggerClick: function (event) {
        var flow = this.props.flow;
        console.log(flow);
        var el = event.target;
        $.ajax({
            type: "POST",
            url: "/flows/" + flow.id + "/plugins/" + this.props.plugin.id,
            contentType: 'application/json',
            data: JSON.stringify(_.find(this.props.plugin.actions, function(o){return ('flow-' + flow.id + '-action-' + o.id === el.getAttribute('id'))}))
        });
    },

    render: function () {
        var plugin = this.props.plugin; 

        var ret = [];
        _.forEach(plugin.actions, function (action) {
            ret.push(<div key={'flow-' + this.props.flow.id + '-action-' + action.id}><input type="button" id={'flow-' + this.props.flow.id + '-action-' + action.id} data-action={action.action} onClick={this.triggerClick} value={action.title}/></div>);
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
        _.forEach(this.props.plugin_list, function (plugin) {
            rows.push(<tr key={'flow-' + flow.id + "-plugin-" + plugin.id + '-actions'}>
                        <td>{plugin.title}</td>
                        <td><PluginAction plugin={plugin} flow={flow}/></td>
                      </tr>);
        });

        return (
            <table className="plugins-table flow">
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

var PluginActionEveryFlowOption = React.createClass({
    triggerChange: function() {
        $.ajax({
            type: "POST",
            url: "/plugins/" + this.props.plugin.id + "/actions/" + this.props.action.id,
            contentType: 'application/json',
            data: JSON.stringify({'every_flow': !this.state.every_flow})
        }).done(function(data){
            if (data.data.success){
                this.setState({every_flow: !this.state.every_flow});
            }
            else
                console.log("Something went wrong trying to change action");
        }.bind(this));
    },

    getInitialState: function () {
        return {every_flow: this.props.initial_every_flow};
    },

    render: function () {
        var action = this.props.action;
        return (
            <div>
                <label htmlFor={action.id}><span className="light">Run on Every Flow: </span><br/>{action.title}</label>
                <input type="checkbox"
                       id={'plugin-' + this.props.plugin.id + '-everyflow-action-' + action.id}
                       data-action={action.action}
                       onChange={this.triggerChange}
                       checked={this.state.every_flow}/>
            </div>);
    }
});

var PluginOption = React.createClass({
    triggerChange: function() {
        $.ajax({
            type: "POST",
            url: "/plugins/" + this.props.plugin.id + "/options/" + this.props.option.id,
            contentType: 'application/json',
            data: JSON.stringify({'value': event.target.value})
        }).done(function(data){
            if (data.data.success) {
                this.setState({value: event.target.value});
            }
            else
                console.log("Something went wrong trying to change option");
        }.bind(this));
    },

    getInitialState: function () {
        return {'value': this.props.option.state.value};
    },

    render: function () {
        var option = this.props.option;
        if (option.type === 'text') {
            return (
                <div>
                <label htmlFor={'plugin-' + this.props.plugin.id + '-option-' + option.id + '-input'}>{option.title}</label>
                <input type="text"
                        id={'plugin-' + this.props.plugin.id + '-option-' + option.id + '-input'}
                        onChange={this.triggerChange}
                        value={this.state.value}/>
                </div>
            );
        } else if (option.type === 'display_only') {
            var json = this.state.value;
            try {
                json = JSON.stringify(JSON.parse(json), null, 2);
            } catch (e) {
            }
            return (
                <div>
                    <pre>{json}</pre>
                </div>
            );
        }
    }
});

var PluginOptionList = React.createClass({
    render: function () {
        var plugin = this.props.plugin; 

        var ret = [];
        _.forEach(plugin.actions, function (action) {
            ret.push(<PluginActionEveryFlowOption key={'plugin-' + plugin.id + '-everyflow-action-' + action.id} action={action} plugin={plugin} initial_every_flow={action.state.every_flow}/>);
        }.bind(this));

        _.forEach(plugin.options, function (option) {
            ret.push(<PluginOption key={'plugin-' + plugin.id + '-option-' + option.id} option={option} plugin={plugin}/>);
        }.bind(this));

        return (<span>{ret}</span>);
    }
});

var PluginOptionsPane = React.createClass({
    getInitialState: function() {
        return {};
    },

    render: function () {

        var rows = [];
        // there's a race condition here if the page is loaded w/ url
        // /plugins. will result in empty options list, we should probably
        // have the pluginList somewhere in state so it can trigger re-render
        _.forEach(this.props.plugin_list, function (plugin) {
            rows.push(<tr key={plugin.id}>
                        <td>{plugin.title}</td>
                        <td><PluginOptionList plugin={plugin}/></td>
                      </tr>);
        });

        return (
            <table className="plugins-table main">
                <thead>
                    <tr><td>Name</td><td>Plugin Options</td></tr>
                </thead>

                <tbody>
                {rows}
                </tbody>
            </table>
        );
    }
});

var PluginsTopLevel = React.createClass({
    getInitialState: function () {
        var pluginList = [];
        $.getJSON("/plugins")
                .done(function (message) {
                    _.each(message.data, function(plugin){
                        if (plugin.type === 'action_plugins') {
                            pluginList.push(plugin);
                        }
                    });

                    this.setState({'plugin_list': pluginList});
                }.bind(this))
                .fail(function () {
                    console.log("Could not fetch plugins");
                }.bind(this));

        return {'plugin_list': pluginList};
    },

    render: function () {
        return (<div><section><PluginOptionsPane plugin_list={this.state.plugin_list}/></section></div>);
    }
});

var PluginsFlowLevel = React.createClass({
    getInitialState: function () {
        var pluginList = [];
        $.getJSON("/plugins")
                .done(function (message) {
                    _.each(message.data, function(plugin){
                        if (plugin.type === 'action_plugins') {
                            pluginList.push(plugin);
                        }
                    });

                    this.setState({'plugin_list': pluginList});
                }.bind(this))
                .fail(function () {
                    console.log("Could not fetch plugins");
                }.bind(this));

        return {'plugin_list': pluginList};
    },

    render: function () {
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;
        return (
            <section>

                <h4>Plugin Actions</h4>

                <PluginActions plugin_list={this.state.plugin_list} flow={flow}/>

            </section>
        );
    }
});

module.exports = {
    'PluginsFlowLevel': PluginsFlowLevel,
    'PluginActions': PluginActions,
    'PluginsTopLevel': PluginsTopLevel
};