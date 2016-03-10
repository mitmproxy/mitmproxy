import React from "react";

import {FlowActions} from "../actions.js";
import {Query} from "../actions.js";
import {Key} from "../utils.js";
import {StoreView} from "../store/view.js";
import Filt from "../filt/filt.js";
import { Router, Splitter} from "./common.js"
import FlowTable from "./flowtable.js";
import FlowView from "./flowview/index.js";

var MainView = React.createClass({
    mixins: [Router],
    contextTypes: {
        flowStore: React.PropTypes.object.isRequired,
    },
    childContextTypes: {
        view: React.PropTypes.object.isRequired,
    },
    getChildContext: function () {
        return {
            view: this.state.view
        };
    },
    getInitialState: function () {
        var sortKeyFun = false;
        var view = new StoreView(this.context.flowStore, this.getViewFilt(), sortKeyFun);
        view.addListener("recalculate", this.onRecalculate);
        view.addListener("add", this.onUpdate);
        view.addListener("update", this.onUpdate);
        view.addListener("remove", this.onUpdate);
        view.addListener("remove", this.onRemove);

        return {
            view: view,
            sortKeyFun: sortKeyFun
        };
    },
    componentWillUnmount: function () {
        this.state.view.close();
    },
    getViewFilt: function () {
        try {
            var filtStr = this.getQuery()[Query.SEARCH];
            var filt = filtStr ? Filt.parse(filtStr) : () => true;
            var highlightStr = this.getQuery()[Query.HIGHLIGHT];
            var highlight = highlightStr ? Filt.parse(highlightStr) : () => false;
        } catch (e) {
            console.error("Error when processing filter: " + e);
        }

        var fun = function filter_and_highlight(flow) {
            if (!this._highlight) {
                this._highlight = {};
            }
            this._highlight[flow.id] = highlight(flow);
            return filt(flow);
        };
        fun.highlightStr = highlightStr;
        fun.filtStr = filtStr;
        return fun;
    },
    componentWillReceiveProps: function (nextProps) {
        var filterChanged = this.state.view.filt.filtStr !== nextProps.location.query[Query.SEARCH];
        var highlightChanged = this.state.view.filt.highlightStr !== nextProps.location.query[Query.HIGHLIGHT];
        if (filterChanged || highlightChanged) {
            this.state.view.recalculate(this.getViewFilt(), this.state.sortKeyFun);
        }
    },
    onRecalculate: function () {
        this.forceUpdate();
        var selected = this.getSelected();
        if (selected) {
            this.refs.flowTable.scrollIntoView(selected);
        }
    },
    onUpdate: function (flow) {
        if (flow.id === this.props.routeParams.flowId) {
            this.forceUpdate();
        }
    },
    onRemove: function (flow_id, index) {
        if (flow_id === this.props.routeParams.flowId) {
            var flow_to_select = this.state.view.list[Math.min(index, this.state.view.list.length - 1)];
            this.selectFlow(flow_to_select);
        }
    },
    setSortKeyFun: function (sortKeyFun) {
        this.setState({
            sortKeyFun: sortKeyFun
        });
        this.state.view.recalculate(this.getViewFilt(), sortKeyFun);
    },
    selectFlow: function (flow) {
        if (flow) {
            var tab = this.props.routeParams.detailTab || "request";
            this.updateLocation(`/flows/${flow.id}/${tab}`);
            this.refs.flowTable.scrollIntoView(flow);
        } else {
            this.updateLocation("/flows");
        }
    },
    selectFlowRelative: function (shift) {
        var flows = this.state.view.list;
        var index;
        if (!this.props.routeParams.flowId) {
            if (shift < 0) {
                index = flows.length - 1;
            } else {
                index = 0;
            }
        } else {
            var currFlowId = this.props.routeParams.flowId;
            var i = flows.length;
            while (i--) {
                if (flows[i].id === currFlowId) {
                    index = i;
                    break;
                }
            }
            index = Math.min(
                Math.max(0, index + shift),
                flows.length - 1);
        }
        this.selectFlow(flows[index]);
    },
    onMainKeyDown: function (e) {
        var flow = this.getSelected();
        if (e.ctrlKey) {
            return;
        }
        switch (e.keyCode) {
            case Key.K:
            case Key.UP:
                this.selectFlowRelative(-1);
                break;
            case Key.J:
            case Key.DOWN:
                this.selectFlowRelative(+1);
                break;
            case Key.SPACE:
            case Key.PAGE_DOWN:
                this.selectFlowRelative(+10);
                break;
            case Key.PAGE_UP:
                this.selectFlowRelative(-10);
                break;
            case Key.END:
                this.selectFlowRelative(+1e10);
                break;
            case Key.HOME:
                this.selectFlowRelative(-1e10);
                break;
            case Key.ESC:
                this.selectFlow(null);
                break;
            case Key.H:
            case Key.LEFT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(-1);
                }
                break;
            case Key.L:
            case Key.TAB:
            case Key.RIGHT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(+1);
                }
                break;
            case Key.C:
                if (e.shiftKey) {
                    FlowActions.clear();
                }
                break;
            case Key.D:
                if (flow) {
                    if (e.shiftKey) {
                        FlowActions.duplicate(flow);
                    } else {
                        FlowActions.delete(flow);
                    }
                }
                break;
            case Key.A:
                if (e.shiftKey) {
                    FlowActions.accept_all();
                } else if (flow && flow.intercepted) {
                    FlowActions.accept(flow);
                }
                break;
            case Key.R:
                if (!e.shiftKey && flow) {
                    FlowActions.replay(flow);
                }
                break;
            case Key.V:
                if (e.shiftKey && flow && flow.modified) {
                    FlowActions.revert(flow);
                }
                break;
            case Key.E:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.promptEdit();
                }
                break;
            case Key.SHIFT:
                break;
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        e.preventDefault();
    },
    getSelected: function () {
        return this.context.flowStore.get(this.props.routeParams.flowId);
    },
    render: function () {
        var selected = this.getSelected();

        var details;
        if (selected) {
            details = [
                <Splitter key="splitter"/>,
                <FlowView
                    key="flowDetails"
                    ref="flowDetails"
                    tab={this.props.routeParams.detailTab}
                    flow={selected}/>
            ];
        } else {
            details = null;
        }

        return (
            <div className="main-view">
                <FlowTable ref="flowTable"
                    selectFlow={this.selectFlow}
                    setSortKeyFun={this.setSortKeyFun}
                    selected={selected} />
                {details}
            </div>
        );
    }
});

export default MainView;
