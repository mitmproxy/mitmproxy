
var React = require("react");
var ReactRouter = require("react-router");
var $ = require("jquery");
var Connection = require("./connection");
var proxyapp = require("./components/proxyapp.js");

$(function () {
    window.ws = new Connection("/updates");

    ReactRouter.run(proxyapp.routes, function (Handler, state) {
        React.render(<Handler/>, document.body);
    });
});

