import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import Splitter from './common/Splitter'
import FlowTable from './FlowTable'
import FlowView from './FlowView'

MainView.propTypes = {
    hasSelection: PropTypes.bool.isRequired,
}

function MainView({ hasSelection }) {
    return (
        <div className="main-view">
            <FlowTable/>
            {hasSelection && <Splitter key="splitter"/>}
            {hasSelection && <FlowView key="flowDetails"/>}
        </div>
    )
}

export default connect(
    state => ({
        hasSelection: !!state.flows.byId[state.flows.selected[0]]
    }),
    {}
)(MainView)
