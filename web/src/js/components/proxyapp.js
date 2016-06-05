import React from "react";
import ReactDOM from "react-dom";
import _ from "lodash";
import {connect} from 'react-redux'
import { Route, Router as ReactRouter, hashHistory, Redirect} from "react-router"

import {Splitter} from "./common.js"
import MainView from "./mainview.js";
import Footer from "./footer.js";
import {Header, MainMenu} from "./header.js";
import EventLog from "./eventlog.js"
import {SettingsStore} from "../store/store.js";
import {Key} from "../utils.js";


//TODO: Move out of here, just a stub.
var Reports = React.createClass({
    render: function () {
        return <div>ReportEditor</div>;
    }
});


var ProxyAppMain = React.createClass({
    childContextTypes: {
        returnFocus: React.PropTypes.func.isRequired,
        location: React.PropTypes.object.isRequired,
    },
    contextTypes: {
        router: React.PropTypes.object.isRequired
    },
    updateLocation: function (pathname, queryUpdate) {
        if (pathname === undefined) {
            pathname = this.props.location.pathname;
        }
        var query = this.props.location.query;
        if (queryUpdate !== undefined) {
            for (var i in queryUpdate) {
                if (queryUpdate.hasOwnProperty(i)) {
                    query[i] = queryUpdate[i] || undefined; //falsey values shall be removed.
                }
            }
        }
        this.context.router.replace({pathname, query});
    },
    getQuery: function () {
        // For whatever reason, react-router always returns the same object, which makes comparing
        // the current props with nextProps impossible. As a workaround, we just clone the query object.
        return _.clone(this.props.location.query);
    },
    componentDidMount: function () {
        this.focus();
        this.settingsStore.addListener("recalculate", this.onSettingsChange);
    },
    componentWillUnmount: function () {
        this.settingsStore.removeListener("recalculate", this.onSettingsChange);
    },
    onSettingsChange: function () {
        this.setState({ settings: this.settingsStore.dict });
    },
    getChildContext: function () {
        return {
            returnFocus: this.focus,
            location: this.props.location
        };
    },
    getInitialState: function () {
        var settingsStore = new SettingsStore();

        this.settingsStore = settingsStore;
        // Default Settings before fetch
        _.extend(settingsStore.dict, {});
        return {
            settings: settingsStore.dict,
        };
    },
    focus: function () {
        document.activeElement.blur();
        window.getSelection().removeAllRanges();
        ReactDOM.findDOMNode(this).focus();
    },
    getMainComponent: function () {
        return this.refs.view.getWrappedInstance ? this.refs.view.getWrappedInstance() : this.refs.view;
    },
    onKeydown: function (e) {

        var selectFilterInput = function (name) {
            var headerComponent = this.refs.header;
            headerComponent.setState({active: MainMenu}, function () {
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
        var query = this.getQuery();
        var eventlog;
        if (this.props.showEventLog) {
            eventlog = [
                <Splitter key="splitter" axis="y"/>,
                <EventLog key="eventlog"/>
            ];
        } else {
            eventlog = null;
        }
        return (
            <div id="container" tabIndex="0" onKeyDown={this.onKeydown}>
                <Header ref="header" settings={this.state.settings} updateLocation={this.updateLocation} query={query} />
                {React.cloneElement(
                    this.props.children,
                    { ref: "view", location: this.props.location , updateLocation: this.updateLocation, query }
                )}
                {eventlog}
                <Footer settings={this.state.settings}/>
            </div>
        );
    }
});

const AppContainer = connect(
    state => ({
        showEventLog: state.eventLog.visible
    })
)(ProxyAppMain);


export var App = (
    <ReactRouter history={hashHistory}>
        <Redirect from="/" to="/flows" />
        <Route path="/" component={AppContainer}>
            <Route path="flows" component={MainView}/>
            <Route path="flows/:flowId/:detailTab" component={MainView}/>
            <Route path="reports" component={Reports}/>
        </Route>
    </ReactRouter>
);
