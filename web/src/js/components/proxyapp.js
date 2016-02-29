var React = require("react");
var ReactDOM = require("react-dom");
var _ = require("lodash");

import {Router, Splitter} from "./common.js"
var common = require("./common.js");
var MainView = require("./mainview.js");
var Footer = require("./footer.js");
var header = require("./header.js");
import EventLog from "./eventlog.js"
var store = require("../store/store.js");
var Query = require("../actions.js").Query;
var Key = require("../utils.js").Key;


//TODO: Move out of here, just a stub.
var Reports = React.createClass({
    render: function () {
        return <div>ReportEditor</div>;
    }
});


var ProxyAppMain = React.createClass({
    mixins: [Router],
    childContextTypes: {
        settingsStore: React.PropTypes.object.isRequired,
        flowStore: React.PropTypes.object.isRequired,
        eventStore: React.PropTypes.object.isRequired,
        returnFocus: React.PropTypes.func.isRequired,
        location: React.PropTypes.object.isRequired,
    },
    componentDidMount: function () {
        this.focus();
    },
    getChildContext: function () {
        return {
            settingsStore: this.state.settingsStore,
            flowStore: this.state.flowStore,
            eventStore: this.state.eventStore,
            returnFocus: this.focus,
            location: this.props.location
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
    focus: function () {
        ReactDOM.findDOMNode(this).focus();
    },
    getMainComponent: function () {
        return this.refs.view;
    },
    onKeydown: function (e) {

        var selectFilterInput = function (name) {
            var headerComponent = this.refs.header;
            headerComponent.setState({active: header.MainMenu}, function () {
                headerComponent.refs.active.refs[name].select();
            });
        }.bind(this);

        switch (e.keyCode) {
            case Key.I:
                selectFilterInput("intercept");
                break;
            case Key.L:
                selectFilterInput("search");
                break;
            case Key.H:
                selectFilterInput("highlight");
                break;
            default:
                var main = this.getMainComponent();
                if (main.onMainKeyDown) {
                    main.onMainKeyDown(e);
                }
                return; // don't prevent default then
        }
        e.preventDefault();
    },
    render: function () {
        var eventlog;
        if (this.props.location.query[Query.SHOW_EVENTLOG]) {
            eventlog = [
                <Splitter key="splitter" axis="y"/>,
                <EventLog key="eventlog"/>
            ];
        } else {
            eventlog = null;
        }
        var children = React.cloneElement(
            this.props.children,
            { ref: "view", location: this.props.location }
        );
        return (
            <div id="container" tabIndex="0" onKeyDown={this.onKeydown}>
                <header.Header ref="header"/>
                {children}
                {eventlog}
                <Footer/>
            </div>
        );
    }
});


import { Route, Router as ReactRouter, hashHistory, Redirect} from "react-router";

export var app = (
<ReactRouter history={hashHistory}>
    <Redirect from="/" to="/flows" />
    <Route path="/" component={ProxyAppMain}>
        <Route path="flows" component={MainView}/>
        <Route path="flows/:flowId/:detailTab" component={MainView}/>
        <Route path="reports" component={Reports}/>
    </Route>
</ReactRouter>
);