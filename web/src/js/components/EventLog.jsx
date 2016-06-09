import React, { PropTypes } from 'react'
import { bindActionCreators } from 'redux'
import { connect } from 'react-redux'
import { toggleEventLogFilter, toggleEventLogVisibility } from '../ducks/eventLog'
import { ToggleButton } from './common'
import EventList from './EventLog/EventList'

EventLog.propTypes = {
    filters: PropTypes.object.isRequired,
    events: PropTypes.array.isRequired,
    onToggleFilter: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired
}

function EventLog({ filters, events, onToggleFilter, onClose }) {
    return (
        <div className="eventlog">
            <div>
                Eventlog
                <div className="pull-right">
                    {['debug', 'info', 'web'].map(type => (
                        <ToggleButton text={type} checked={filters[type]} onToggle={() => onToggleFilter(type)}/>
                    ))}
                    <i onClick={onClose} className="fa fa-close"></i>
                </div>
            </div>
            <EventList events={events} />
        </div>
    )
}

export default connect(
    state => ({
        filters: state.eventLog.filter,
        events: state.eventLog.filteredEvents,
    }),
    dispatch => bindActionCreators({
        onClose: toggleEventLogVisibility,
        onToggleFilter: toggleEventLogFilter,
    }, dispatch)
)(EventLog)
