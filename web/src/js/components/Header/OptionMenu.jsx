import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import ToggleButton from '../common/ToggleButton'
import ToggleInputButton from '../common/ToggleInputButton'
import { updateSettings } from '../../ducks/settings'

OptionMenu.title = 'Options'

OptionMenu.propTypes = {
    settings: PropTypes.object.isRequired,
    onSettingsChange: PropTypes.func.isRequired,
}

function OptionMenu({ settings, onSettingsChange }) {
    // @todo use settings.map
    return (
        <div>
            <div className="menu-row">
                <ToggleButton text="showhost"
                    checked={settings.showhost}
                    onToggle={() => onSettingsChange({ showhost: !settings.showhost })}
                />
                <ToggleButton text="no_upstream_cert"
                    checked={settings.no_upstream_cert}
                    onToggle={() => onSettingsChange({ no_upstream_cert: !settings.no_upstream_cert })}
                />
                <ToggleButton text="rawtcp"
                    checked={settings.rawtcp}
                    onToggle={() => onSettingsChange({ rawtcp: !settings.rawtcp })}
                />
                <ToggleButton text="http2"
                    checked={settings.http2}
                    onToggle={() => onSettingsChange({ http2: !settings.http2 })}
                />
                <ToggleButton text="anticache"
                    checked={settings.anticache}
                    onToggle={() => onSettingsChange({ anticache: !settings.anticache })}
                />
                <ToggleButton text="anticomp"
                    checked={settings.anticomp}
                    onToggle={() => onSettingsChange({ anticomp: !settings.anticomp })}
                />
                <ToggleInputButton name="stickyauth" placeholder="Sticky auth filter"
                    checked={!!settings.stickyauth}
                    txt={settings.stickyauth || ''}
                    onToggleChanged={txt => onSettingsChange({ stickyauth: !settings.stickyauth ? txt : null })}
                />
                <ToggleInputButton name="stickycookie" placeholder="Sticky cookie filter"
                    checked={!!settings.stickycookie}
                    txt={settings.stickycookie || ''}
                    onToggleChanged={txt => onSettingsChange({ stickycookie: !settings.stickycookie ? txt : null })}
                />
                <ToggleInputButton name="stream" placeholder="stream..."
                    checked={!!settings.stream}
                    txt={settings.stream || ''}
                    inputType="number"
                    onToggleChanged={txt => onSettingsChange({ stream: !settings.stream ? txt : null })}
                />
            </div>
            <div className="clearfix"/>
        </div>
    )
}

export default connect(
    state => ({
        settings: state.settings.settings,
    }),
    {
        onSettingsChange: updateSettings,
    }
)(OptionMenu)
