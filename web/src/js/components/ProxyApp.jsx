import React, { Component, PropTypes } from 'react'
import ReactDOM from 'react-dom'
import _ from 'lodash'
import { connect } from 'react-redux'

import { init as appInit, destruct as appDestruct } from '../ducks/app'
import Header from './Header'
import EventLog from './EventLog'
import Footer from './Footer'
import { SettingsStore } from '../store/store.js'
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

        this.settingsStore = new SettingsStore()

        // Default Settings before fetch
        _.extend(this.settingsStore.dict, {})

        this.state = { settings: this.settingsStore.dict }

        this.focus = this.focus.bind(this)
        this.onKeyDown = this.onKeyDown.bind(this)
        this.updateLocation = this.updateLocation.bind(this)
        this.onSettingsChange = this.onSettingsChange.bind(this)
    }

    componentWillMount() {
        this.props.appInit()
    }

    /**
     * @todo move to actions
     */
    updateLocation(pathname, queryUpdate) {
        if (pathname === undefined) {
            pathname = this.props.location.pathname
        }
        const query = this.props.location.query
        for (const key of Object.keys(queryUpdate || {})) {
            query[key] = queryUpdate[key] || undefined
        }
        this.context.router.replace({ pathname, query })
    }

    /**
     * @todo pass in with props
     */
    getQuery() {
        // For whatever reason, react-router always returns the same object, which makes comparing
        // the current props with nextProps impossible. As a workaround, we just clone the query object.
        return _.clone(this.props.location.query)
    }

    /**
     * @todo remove settings store
     * @todo connect websocket here
     * @todo listen to window's key events
     */
    componentDidMount() {
        this.focus()
        this.settingsStore.addListener('recalculate', this.onSettingsChange)
    }

    /**
     * @todo remove settings store
     * @todo disconnect websocket here
     * @todo stop listening to window's key events
     */
    componentWillUnmount() {
        this.props.appDestruct()
        this.settingsStore.removeListener('recalculate', this.onSettingsChange)
    }

    /**
     * @todo move to actions
     */
    onSettingsChange() {
        this.setState({ settings: this.settingsStore.dict })
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
        let name = null

        switch (e.keyCode) {
            case Key.I:
                name = 'intercept'
                break
            case Key.L:
                name = 'search'
                break
            case Key.H:
                name = 'highlight'
                break
            default:
                let main = this.refs.view
                if (this.refs.view.getWrappedInstance) {
                    main = this.refs.view.getWrappedInstance()
                }
                if (main.onMainKeyDown) {
                    main.onMainKeyDown(e)
                }
                return // don't prevent default then
        }

        if (name) {
            const headerComponent = this.refs.header
            headerComponent.setState({ active: Header.entries[0] }, () => {
                headerComponent.refs.active.refs[name].select()
            })
        }

        e.preventDefault()
    }

    render() {
        const { showEventLog, location, children } = this.props
        const { settings } = this.state
        const query = this.getQuery()
        return (
            <div id="container" tabIndex="0" onKeyDown={this.onKeyDown}>
                <Header ref="header" settings={settings} updateLocation={this.updateLocation} query={query} />
                {React.cloneElement(
                    children,
                    { ref: 'view', location, query, updateLocation: this.updateLocation }
                )}
                {showEventLog && (
                    <EventLog key="eventlog"/>
                )}
                <Footer settings={settings}/>
            </div>
        )
    }
}

export default connect(
    state => ({
        showEventLog: state.eventLog.visible
    }),
    {
        appInit,
        appDestruct,
    }
)(ProxyAppMain)
