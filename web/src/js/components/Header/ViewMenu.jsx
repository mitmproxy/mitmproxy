import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import { ToggleButton } from '../common.js'
import { toggleEventLogVisibility } from '../../ducks/eventLog'

ViewMenu.title = 'View'
ViewMenu.route = 'flows'

ViewMenu.propTypes = {
    visible: PropTypes.bool.isRequired,
    onToggle: PropTypes.func.isRequired,
}

function ViewMenu({ visible, onToggle }) {
    return (
        <div>
            <div className="menu-row">
                <ToggleButton text="Show Event Log" checked={visible} onToggle={onToggle} />
            </div>
            <div className="clearfix"></div>
        </div>
    )
}

export default connect(
    state => ({
        visible: state.eventLog.visible,
    }),
    {
        onToggle: toggleEventLogVisibility,
    }
)(ViewMenu)
