import React, { Component, PropTypes } from 'react'
import ReactDOM from 'react-dom'
import _ from 'lodash'
import { connect } from 'react-redux'

import { init as appInit, destruct as appDestruct } from '../ducks/app'
import { onKeyDown } from '../ducks/ui'
import Header from './Header'
import EventLog from './EventLog'
import Footer from './Footer'
import { Key } from '../utils.js'

class ProxyAppMain extends Component {

    static childContextTypes = {
        returnFocus: PropTypes.func.isRequired,
    }

    static contextTypes = {
        router: PropTypes.object.isRequired,
    }

    constructor(props, context) {
        super(props, context)

        this.focus = this.focus.bind(this)
        this.onKeyDown = this.onKeyDown.bind(this)
    }

    componentWillMount() {
        this.props.appInit()
    }

    componentWillReceiveProps(nextProps) {
        if(nextProps.query === this.props.query && nextProps.flowId === this.props.flowId && nextProps.panel === this.props.panel) {
            return
        }
        if(nextProps.flowId) {
            this.context.router.replace({ pathname: `/flows/${nextProps.flowId}/${nextProps.panel}`, query: nextProps.query })
        } else {
            this.context.router.replace({ pathname: '/flows', query: nextProps.query })
        }
    }

    /**
     * @todo listen to window's key events
     */
    componentDidMount() {
        this.focus()
    }

    componentWillUnmount() {
        this.props.appDestruct()
    }

    /**
     * @todo use props
     */
    getChildContext() {
        return { returnFocus: this.focus }
    }

    /**
     * @todo remove it
     */
    focus() {
        document.activeElement.blur()
        window.getSelection().removeAllRanges()
        ReactDOM.findDOMNode(this).focus()
    }

    /**
     * @todo move to actions
     * @todo bind on window
     */
    onKeyDown(e) {
        if (e.ctrlKey) {
            return
        }
        this.props.onKeyDown(e.keyCode, e.shiftKey)
        e.preventDefault()
    }

    render() {
        const { showEventLog, location, children, query } = this.props
        return (
            <div id="container" tabIndex="0" onKeyDown={this.onKeyDown}>
                <Header ref="header" query={query} />
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
        settings: state.settings.settings,
        query: state.ui.query,
        panel: state.ui.panel,
        flowId: state.flows.views.main.selected[0]
    }),
    {
        appInit,
        appDestruct,
        onKeyDown
    }
)(ProxyAppMain)
