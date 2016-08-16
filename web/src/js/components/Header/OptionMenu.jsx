import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import ToggleButton from '../common/ToggleButton'
import ToggleInputButton from '../common/ToggleInputButton'
import { update as updateSettings } from '../../ducks/settings'

OptionMenu.title = 'Options'

OptionMenu.propTypes = {
    settings: PropTypes.object.isRequired,
    updateSettings: PropTypes.func.isRequired,
}

function OptionMenu({ settings, updateSettings }) {
    return (
        <div>
            <div className="menu-row">
                <ToggleButton text="showhost"
                    checked={settings.showhost}
                    onToggle={() => updateSettings({ showhost: !settings.showhost })}
                />
                <ToggleButton text="no_upstream_cert"
                    checked={settings.no_upstream_cert}
                    onToggle={() => updateSettings({ no_upstream_cert: !settings.no_upstream_cert })}
                />
                <ToggleButton text="rawtcp"
                    checked={settings.rawtcp}
                    onToggle={() => updateSettings({ rawtcp: !settings.rawtcp })}
                />
                <ToggleButton text="http2"
                    checked={settings.http2}
                    onToggle={() => updateSettings({ http2: !settings.http2 })}
                />
                <ToggleButton text="anticache"
                    checked={settings.anticache}
                    onToggle={() => updateSettings({ anticache: !settings.anticache })}
                />
                <ToggleButton text="anticomp"
                    checked={settings.anticomp}
                    onToggle={() => updateSettings({ anticomp: !settings.anticomp })}
                />
                <ToggleInputButton name="stickyauth" placeholder="Sticky auth filter"
                    checked={!!settings.stickyauth}
                    txt={settings.stickyauth}
                    onToggleChanged={txt => updateSettings({ stickyauth: !settings.stickyauth ? txt : null })}
                />
                <ToggleInputButton name="stickycookie" placeholder="Sticky cookie filter"
                    checked={!!settings.stickycookie}
                    txt={settings.stickycookie}
                    onToggleChanged={txt => updateSettings({ stickycookie: !settings.stickycookie ? txt : null })}
                />
                <ToggleInputButton name="stream" placeholder="stream..."
                    checked={!!settings.stream}
                    txt={settings.stream}
                    inputType="number"
                    onToggleChanged={txt => updateSettings({ stream: !settings.stream ? txt : null })}
                />
            </div>
            <div className="clearfix"/>
        </div>
    )
}

export default connect(
    state => ({
        settings: state.settings,
    }),
    {
        updateSettings,
    }
)(OptionMenu)
