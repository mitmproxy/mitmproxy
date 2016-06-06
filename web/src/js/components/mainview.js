import React from "react";

import {FlowActions} from "../actions.js";
import {Query} from "../actions.js";
import {Key} from "../utils.js";
import {Splitter} from "./common.js"
import FlowTable from "./flowtable.js";
import FlowView from "./flowview/index.js";
import {connect} from 'react-redux'
import {selectFlow, setFilter, setHighlight, setSort} from "../ducks/flows";


var MainView = React.createClass({
    componentWillReceiveProps: function (nextProps) {
        // Update redux store with route changes
        if(nextProps.routeParams.flowId !== (nextProps.selectedFlow || {}).id) {
            this.props.selectFlow(nextProps.routeParams.flowId)
        }
        if(nextProps.location.query[Query.SEARCH] !== nextProps.filter) {
            this.props.setFilter(nextProps.location.query[Query.SEARCH], false)
        }
        if (nextProps.location.query[Query.HIGHLIGHT] !== nextProps.highlight) {
            this.props.setHighlight(nextProps.location.query[Query.HIGHLIGHT], false)
        }
    },
    selectFlow: function (flow) {
        // TODO: This belongs into redux
        if (flow) {
            let tab = this.props.routeParams.detailTab || "request";
            this.props.updateLocation(`/flows/${flow.id}/${tab}`);
        } else {
            this.props.updateLocation("/flows");
        }
    },
    selectFlowRelative: function (shift) {
        // TODO: This belongs into redux
        let flows = this.props.flows,
            index
        if (!this.props.routeParams.flowId) {
            if (shift < 0) {
                index = flows.length - 1
            } else {
                index = 0
            }
        } else {
            index = flows.indexOf(this.props.selectedFlow)
            index = Math.min(
                Math.max(0, index + shift),
                flows.length - 1
            )
        }
        this.selectFlow(flows[index])
    },
    onMainKeyDown: function (e) {
        var flow = this.props.selectedFlow;
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
    render: function () {

        var details = null;
        if (this.props.selectedFlow) {
            details = [
                <Splitter key="splitter"/>,
                <FlowView
                    key="flowDetails"
                    ref="flowDetails"
                    tab={this.props.routeParams.detailTab}
                    query={this.props.query}
                    updateLocation={this.props.updateLocation}
                    flow={this.props.selectedFlow}/>
            ]
        }

        return (
            <div className="main-view">
                <FlowTable ref="flowTable"
                    selectFlow={this.selectFlow}
                    setSort={this.props.setSort}
                    selected={this.props.selectedFlow} />
                {details}
            </div>
        );
    }
});

const MainViewContainer = connect(
    state => ({
        flows: state.flows.view,
        filter: state.flows.filter,
        sort: state.flows.sort,
        highlight: state.flows.highlight,
        selectedFlow: state.flows.all.byId[state.flows.selected[0]]
    }),
    dispatch => ({
        selectFlow: flowId => dispatch(selectFlow(flowId)),
        setFilter: filter => dispatch(setFilter(filter)),
        setSort: (sort) => dispatch(setSort(sort)),
        setHighlight: highlight => dispatch(setHighlight(highlight))
    }),
    undefined,
    {withRef: true}
)(MainView);

export default MainViewContainer;
