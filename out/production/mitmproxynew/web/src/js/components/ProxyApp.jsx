import React, { Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { onKeyDown } from '../ducks/ui/keyboard'
import MainView from './MainView'
import Header from './Header'
import EventLog from './EventLog'
import Footer from './Footer'
import Modal from './Modal/Modal'

class ProxyAppMain extends Component {

    componentWillMount() {
        window.addEventListener('keydown', this.props.onKeyDown);
    }

    componentWillUnmount() {
        window.removeEventListener('keydown', this.props.onKeyDown);
    }

    render() {
        const { showEventLog } = this.props
        return (
            <div id="container" tabIndex="0">
                <Header/>
                <MainView />
                {showEventLog && (
                    <EventLog key="eventlog"/>
                )}
                <Footer />
                <Modal/>
            </div>
        )
    }
}

export default connect(
    state => ({
        showEventLog: state.eventLog.visible,
    }),
    {
        onKeyDown,
    }
)(ProxyAppMain)
