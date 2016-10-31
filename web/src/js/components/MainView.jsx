import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import Splitter from './common/Splitter'
import FlowTable from './FlowTable'
import FlowView from './FlowView'
import * as flowsActions from '../ducks/flows'

class MainView extends Component {

    static propTypes = {
        highlight: PropTypes.string,
        sort: PropTypes.object,
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
                    onSelect={this.props.selectFlow}
                />
                {selectedFlow && [
                    <Splitter key="splitter"/>,
                    <FlowView
                        key="flowDetails"
                        ref="flowDetails"
                        tab={this.props.tab}
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
        flows: state.flows.view,
        filter: state.flows.filter,
        highlight: state.flows.highlight,
        selectedFlow: state.flows.byId[state.flows.selected[0]],
        tab: state.ui.flow.tab,
    }),
    {
        selectFlow: flowsActions.select,
        updateFlow: flowsActions.update,
    }
)(MainView)
