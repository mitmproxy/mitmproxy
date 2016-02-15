var React = require("react");
var ReactRouter = require("react-router");
var $ = require("jquery");
var Connection = require("./connection");
var proxyapp = require("./components/proxyapp.js");
var EventLogActions = require("./actions.js").EventLogActions;

$(function () {
    window.ws = new Connection("/updates");

    window.onerror = function (msg) {
        EventLogActions.add_event(msg);
    };

    ReactRouter.run(proxyapp.routes, function (Handler, state) {
        React.render(<Handler/>, document.body);
    });
});

