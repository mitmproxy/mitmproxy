import React from "react";

import {FlowActions} from "../../actions.js";

var NavAction = React.createClass({
    onClick: function (e) {
        e.preventDefault();
        this.props.onClick();
    },
    render: function () {
        return (
            <a title={this.props.title}
                href="#"
                className="nav-action"
                onClick={this.onClick}>
                <i className={"fa fa-fw " + this.props.icon}></i>
            </a>
        );
    }
});

var Nav = React.createClass({
    render: function () {
        var flow = this.props.flow;

        var tabs = this.props.tabs.map(function (e) {
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function (event) {
                this.props.selectTab(e);
                event.preventDefault();
            }.bind(this);
            return <a key={e}
                href="#"
                className={className}
                onClick={onClick}>{str}</a>;
        }.bind(this));

        var acceptButton = null;
        if(flow.intercepted){
            acceptButton = <NavAction title="[a]ccept intercepted flow" icon="fa-play" onClick={FlowActions.accept.bind(null, flow)} />;
        }
        var revertButton = null;
        if(flow.modified){
            revertButton = <NavAction title="revert changes to flow [V]" icon="fa-history" onClick={FlowActions.revert.bind(null, flow)} />;
        }

        return (
            <nav ref="head" className="nav-tabs nav-tabs-sm">
                {tabs}
                <NavAction title="[d]elete flow" icon="fa-trash" onClick={FlowActions.delete.bind(null, flow)} />
                <NavAction title="[D]uplicate flow" icon="fa-copy" onClick={FlowActions.duplicate.bind(null, flow)} />
                <NavAction disabled title="[r]eplay flow" icon="fa-repeat" onClick={FlowActions.replay.bind(null, flow)} />
                {acceptButton}
                {revertButton}
            </nav>
        );
    }
});

export default Nav;