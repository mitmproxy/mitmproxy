import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { Query } from '../actions.js'
import { Key } from '../utils.js'
import Splitter from './common/Splitter'
import FlowTable from './FlowTable'
import FlowView from './FlowView'
import * as flowsActions from '../ducks/flows'
import { select as selectFlow, updateFilter, updateHighlight } from '../ducks/views/main'

class MainView extends Component {

    static propTypes = {
        highlight: PropTypes.string,
        sort: PropTypes.object,
    }

    /**
     * @todo move to actions
     * @todo replace with mapStateToProps
     */
    componentWillReceiveProps(nextProps) {
        // Update redux store with route changes
        if (nextProps.routeParams.flowId !== (nextProps.selectedFlow || {}).id) {
            this.props.selectFlow(nextProps.routeParams.flowId)
        }
        if (nextProps.location.query[Query.SEARCH] !== nextProps.filter) {
            this.props.updateFilter(nextProps.location.query[Query.SEARCH], false)
        }
        if (nextProps.location.query[Query.HIGHLIGHT] !== nextProps.highlight) {
            this.props.updateHighlight(nextProps.location.query[Query.HIGHLIGHT], false)
        }
    }

    /**
     * @todo move to actions
     */
    selectFlow(flow) {
        if (flow) {
            this.props.updateLocation(`/flows/${flow.id}/${this.props.routeParams.detailTab || 'request'}`)
        } else {
            this.props.updateLocation('/flows')
        }
    }

    /**
     * @todo move to actions
     */
    selectFlowRelative(shift) {
        const { flows, routeParams, selectedFlow } = this.props
        let index = 0
        if (!routeParams.flowId) {
            if (shift < 0) {
                index = flows.length - 1
            }
        } else {
            index = Math.min(
                Math.max(0, flows.indexOf(selectedFlow) + shift),
                flows.length - 1
            )
        }
        this.selectFlow(flows[index])
    }

    /**
     * @todo move to actions
     */
    onMainKeyDown(e) {
        var flow = this.props.selectedFlow
        if (e.ctrlKey) {
            return
        }
        switch (e.keyCode) {
            case Key.K:
            case Key.UP:
                this.selectFlowRelative(-1)
                break
            case Key.J:
            case Key.DOWN:
                this.selectFlowRelative(+1)
                break
            case Key.SPACE:
            case Key.PAGE_DOWN:
                this.selectFlowRelative(+10)
                break
            case Key.PAGE_UP:
                this.selectFlowRelative(-10)
                break
            case Key.END:
                this.selectFlowRelative(+1e10)
                break
            case Key.HOME:
                this.selectFlowRelative(-1e10)
                break
            case Key.ESC:
                this.selectFlow(null)
                break
            case Key.H:
            case Key.LEFT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(-1)
                }
                break
            case Key.L:
            case Key.TAB:
            case Key.RIGHT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(+1)
                }
                break
            case Key.C:
                if (e.shiftKey) {
                    this.props.clearFlows()
                }
                break
            case Key.D:
                if (flow) {
                    if (e.shiftKey) {
                        this.props.duplicateFlow(flow)
                    } else {
                        this.props.removeFlow(flow)
                    }
                }
                break
            case Key.A:
                if (e.shiftKey) {
                    this.props.acceptAllFlows()
                } else if (flow && flow.intercepted) {
                    this.props.acceptFlow(flow)
                }
                break
            case Key.R:
                if (!e.shiftKey && flow) {
                    this.props.replayFlow(flow)
                }
                break
            case Key.V:
                if (e.shiftKey && flow && flow.modified) {
                    this.props.revertFlow(flow)
                }
                break
            case Key.E:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.promptEdit()
                }
                break
            case Key.SHIFT:
                break
            default:
                console.debug('keydown', e.keyCode)
                return
        }
        e.preventDefault()
    }

    render() {
        const { flows, selectedFlow, highlight } = this.props
        return (
            <div className="main-view">
                <FlowTable
                    ref="flowTable"
                    flows={flows}
                    selected={selectedFlow}
                    highlight={highlight}
                    onSelect={flow => this.selectFlow(flow)}
                />
                {selectedFlow && [
                    <Splitter key="splitter"/>,
                    <FlowView
                        key="flowDetails"
                        ref="flowDetails"
                        tab={this.props.routeParams.detailTab}
                        query={this.props.query}
                        updateLocation={this.props.updateLocation}
                        updateFlow={data => this.props.updateFlow(selectedFlow, data)}
                        flow={selectedFlow}
                    />
                ]}
            </div>
        )
    }
}

export default connect(
    state => ({
        flows: state.flows.views.main.view.data,
        filter: state.flows.views.main.filter,
        highlight: state.flows.views.main.highlight,
        selectedFlow: state.flows.list.byId[state.flows.views.main.selected[0]]
    }),
    {
        selectFlow,
        updateFilter,
        updateHighlight,
        updateFlow: flowsActions.update,
        clearFlows: flowsActions.clear,
        duplicateFlow: flowsActions.duplicate,
        removeFlow: flowsActions.remove,
        acceptAllFlows: flowsActions.acceptAll,
        acceptFlow: flowsActions.accept,
        replayFlow: flowsActions.replay,
        revertFlow: flowsActions.revert,
    },
    undefined,
    { withRef: true }
)(MainView)
