var React = require("react");
var _ = require("lodash");

var utils = require("../../utils.js");
var MessageUtils = require("../../flow/utils.js").MessageUtils;

var PluginOptionsPane = React.createClass({
    getInitialState: function() {
        return {};
    },

    render: function () {
        var rows = [];
        _.forEach(this.props.plugin_list, function (plugin) {
            rows.push(<tr key={plugin.id}>
                        <td>{plugin.title}</td>
                        <td></td>
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
                        //if (plugin.type === 'action_plugins') {
                            pluginList.push(plugin);
                        //}
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


module.exports = {
    'PluginsTopLevel': PluginsTopLevel
};