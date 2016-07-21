import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'

import { init as appInit, destruct as appDestruct } from '../ducks/app'
import { onKeyDown } from '../ducks/ui/keyboard'
import Header from './Header'
import EventLog from './EventLog'
import Footer from './Footer'

class ProxyAppMain extends Component {

    static contextTypes = {
        router: PropTypes.object.isRequired,
    }

    componentWillMount() {
        this.props.appInit(this.context.router)
        window.addEventListener('keydown', this.props.onKeyDown);
    }

    componentWillUnmount() {
        this.props.appDestruct(this.context.router)
        window.removeEventListener('keydown', this.props.onKeyDown);
    }

    componentWillReceiveProps(nextProps) {
        /*
        FIXME: improve react-router -> redux integration.
        if (nextProps.location.query[Query.SEARCH] !== nextProps.filter) {
            this.props.updateFilter(nextProps.location.query[Query.SEARCH], false)
        }
        if (nextProps.location.query[Query.HIGHLIGHT] !== nextProps.highlight) {
            this.props.updateHighlight(nextProps.location.query[Query.HIGHLIGHT], false)
        }
        */
        if (nextProps.query === this.props.query && nextProps.selectedFlowId === this.props.selectedFlowId && nextProps.panel === this.props.panel) {
            return
        }
        if (nextProps.selectedFlowId) {
            this.context.router.replace({ pathname: `/flows/${nextProps.selectedFlowId}/${nextProps.panel}`, query: nextProps.query })
        } else {
            this.context.router.replace({ pathname: '/flows', query: nextProps.query })
        }

    }

    render() {
        const { showEventLog, location, children, query } = this.props
        return (
            <div id="container" tabIndex="0">
                <Header/>
                {React.cloneElement(
                    children,
                    { ref: 'view', location, query }
                )}
                {showEventLog && (
                    <EventLog key="eventlog"/>
                )}
                <Footer />
            </div>
        )
    }
}

export default connect(
    state => ({
        showEventLog: state.eventLog.visible,
        query: state.flowView.filter,
        panel: state.ui.flow.tab,
        selectedFlowId: state.flows.selected[0]
    }),
    {
        appInit,
        appDestruct,
        onKeyDown
    }
)(ProxyAppMain)
