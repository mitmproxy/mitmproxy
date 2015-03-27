var React = require("react");
var ReactRouter = require("react-router");
var _ = require("lodash");

var common = require("./common.js");
var MainView = require("./mainview.js");
var Footer = require("./footer.js");
var header = require("./header.js");
var EventLog = require("./eventlog.js");
var store = require("../store/store.js");
var Query = require("../actions.js").Query;


//TODO: Move out of here, just a stub.
var Reports = React.createClass({
    render: function () {
        return <div>ReportEditor</div>;
    }
});


var ProxyAppMain = React.createClass({
    mixins: [common.RouterState],
    childContextTypes: {
        settingsStore: React.PropTypes.object.isRequired,
        flowStore: React.PropTypes.object.isRequired,
        eventStore: React.PropTypes.object.isRequired
    },
    getChildContext: function () {
        return {
            settingsStore: this.state.settingsStore,
            flowStore: this.state.flowStore,
            eventStore: this.state.eventStore
        };
    },
    getInitialState: function () {
        var eventStore = new store.EventLogStore();
        var flowStore = new store.FlowStore();
        var settingsStore = new store.SettingsStore();

        // Default Settings before fetch
        _.extend(settingsStore.dict, {});
        return {
            settingsStore: settingsStore,
            flowStore: flowStore,
            eventStore: eventStore
        };
    },
    render: function () {
        var eventlog;
        if (this.getQuery()[Query.SHOW_EVENTLOG]) {
            eventlog = [
                <common.Splitter key="splitter" axis="y"/>,
                <EventLog key="eventlog"/>
            ];
        } else {
            eventlog = null;
        }
        return (
            <div id="container">
                <header.Header/>
                <RouteHandler query={this.getQuery()}/>
                {eventlog}
                <Footer/>
            </div>
        );
    }
});


var Route = ReactRouter.Route;
var RouteHandler = ReactRouter.RouteHandler;
var Redirect = ReactRouter.Redirect;
var DefaultRoute = ReactRouter.DefaultRoute;
var NotFoundRoute = ReactRouter.NotFoundRoute;


var routes = (
    <Route path="/" handler={ProxyAppMain}>
        <Route name="flows" path="flows" handler={MainView}/>
        <Route name="flow" path="flows/:flowId/:detailTab" handler={MainView}/>
        <Route name="reports" handler={Reports}/>
        <Redirect path="/" to="flows" />
    </Route>
);

module.exports = {
    routes: routes
};