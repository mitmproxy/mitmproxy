import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { createHashHistory, useQueries } from 'history'

import { init as appInit, destruct as appDestruct } from '../ducks/app'
import { onKeyDown } from '../ducks/ui/keyboard'
import { updateFilter, updateHighlight } from '../ducks/flowView'
import { selectTab } from '../ducks/ui/flow'
import { select as selectFlow } from '../ducks/flows'
import { Query } from '../actions'
import MainView from './MainView'
import Header from './Header'
import EventLog from './EventLog'
import Footer from './Footer'

class ProxyAppMain extends Component {

    flushToStore(location) {
        const components = location.pathname.split('/').filter(v => v)
        const query = location.query || {}

        if (components.length > 2) {
            this.props.selectFlow(components[1])
            this.props.selectTab(components[2])
        } else {
            this.props.selectFlow(null)
            this.props.selectTab(null)
        }

        this.props.updateFilter(query[Query.SEARCH])
        this.props.updateHighlight(query[Query.HIGHLIGHT])
    }

    flushToHistory(nextProps) {
        const query = { ...query }

        if (nextProps.filter) {
            query[Query.SEARCH] = nextProps.filter
        }

        if (nextProps.highlight) {
            query[Query.HIGHLIGHT] = nextProps.highlight
        }

        if (nextProps.selectedFlowId) {
            this.history.push({ pathname: `/flows/${nextProps.selectedFlowId}/${nextProps.tab}`, query })
        } else {
            this.history.push({ pathname: '/flows', query })
        }
    }

    componentWillMount() {
        this.props.appInit()
        this.history = useQueries(createHashHistory)()
        this.unlisten = this.history.listen(location => this.flushToStore(location))
        this.flushToStore(this.history.getCurrentLocation())
        window.addEventListener('keydown', this.props.onKeyDown)
    }

    componentWillUnmount() {
        this.props.appDestruct()
        this.unlisten()
        window.removeEventListener('keydown', this.props.onKeyDown)
    }

    componentWillReceiveProps(nextProps) {
        this.flushToHistory(nextProps)
    }

    render() {
        return (
            <div id="container" tabIndex="0">
                <Header/>
                <MainView />
                {this.props.showEventLog && (
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
    }),
    {
        appInit,
        appDestruct,
        onKeyDown,
        updateFilter,
        updateHighlight,
        selectTab,
        selectFlow
    }
)(ProxyAppMain)
