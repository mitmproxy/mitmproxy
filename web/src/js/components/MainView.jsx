import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { Query } from '../actions.js'
import Splitter from './common/Splitter'
import FlowTable from './FlowTable'
import FlowView from './FlowView'
import * as flowsActions from '../ducks/flows'
import { updateFilter, updateHighlight } from '../ducks/flowView'

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
        if (nextProps.location.query[Query.SEARCH] !== nextProps.filter) {
            this.props.updateFilter(nextProps.location.query[Query.SEARCH], false)
        }
        if (nextProps.location.query[Query.HIGHLIGHT] !== nextProps.highlight) {
            this.props.updateHighlight(nextProps.location.query[Query.HIGHLIGHT], false)
        }
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
                    onSelect={flow => this.props.selectFlow(flow.id)}
                />
                {selectedFlow && [
                    <Splitter key="splitter"/>,
                    <FlowView
                        key="flowDetails"
                        ref="flowDetails"
                        tab={this.props.routeParams.detailTab}
                        query={this.props.query}
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
        flows: state.flowView.data,
        filter: state.flowView.filter,
        highlight: state.flowView.highlight,
        selectedFlow: state.flows.byId[state.flows.selected[0]]
    }),
    {
        selectFlow: flowsActions.select,
        updateFilter,
        updateHighlight,
        updateFlow: flowsActions.update,
    },
    undefined,
    {
        withRef: true
    }
)(MainView)
