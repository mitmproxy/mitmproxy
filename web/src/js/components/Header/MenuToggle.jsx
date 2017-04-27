import PropTypes from 'prop-types'
import { connect } from "react-redux"
import { update as updateSettings } from "../../ducks/settings"
import { toggleVisibility } from "../../ducks/eventLog"

MenuToggle.propTypes = {
    value: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired,
    children: PropTypes.node.isRequired,
}

export function MenuToggle({ value, onChange, children }) {
    return (
        <div className="menu-entry">
            <label>
                <input type="checkbox"
                       checked={value}
                       onChange={onChange}/>
                {children}
            </label>
        </div>
    )
}


SettingsToggle.propTypes = {
    setting: PropTypes.string.isRequired,
    children: PropTypes.node.isRequired,
}

export function SettingsToggle({ setting, children, settings, updateSettings }) {
    return (
        <MenuToggle
            value={settings[setting] || false} // we don't have settings initially, so just pass false.
            onChange={() => updateSettings({ [setting]: !settings[setting] })}
        >
            {children}
        </MenuToggle>
    )
}
SettingsToggle = connect(
    state => ({
        settings: state.settings,
    }),
    {
        updateSettings,
    }
)(SettingsToggle)


export function EventlogToggle({ toggleVisibility, eventLogVisible }) {
    return (
        <MenuToggle
            value={eventLogVisible}
            onChange={toggleVisibility}
        >
            Display Event Log
        </MenuToggle>
    )
}
EventlogToggle = connect(
    state => ({
        eventLogVisible: state.eventLog.visible,
    }),
    {
        toggleVisibility,
    }
)(EventlogToggle)

