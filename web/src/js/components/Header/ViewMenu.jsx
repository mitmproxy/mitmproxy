import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import ToggleButton from '../common/ToggleButton'
import { toggleVisibility } from '../../ducks/eventLog'

ViewMenu.title = 'View'
ViewMenu.route = 'flows'

ViewMenu.propTypes = {
    eventLogVisible: PropTypes.bool.isRequired,
    toggleEventLog: PropTypes.func.isRequired,
}

function ViewMenu({ eventLogVisible, toggleEventLog }) {
    return (
        <div>
            <div className="menu-row">
                <ToggleButton text="Show Event Log" checked={eventLogVisible} onToggle={toggleEventLog} />
            </div>
            <div className="clearfix"></div>
        </div>
    )
}

export default connect(
    state => ({
        eventLogVisible: state.eventLog.visible,
    }),
    {
        toggleEventLog: toggleVisibility,
    }
)(ViewMenu)
