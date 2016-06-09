import React, { PropTypes } from 'react'
import { ToggleInputButton, ToggleButton } from '../common.js'
import { SettingsActions } from '../../actions.js'

OptionMenu.title = "Options"

OptionMenu.propTypes = {
    settings: PropTypes.object.isRequired,
}

export default function OptionMenu({ settings }) {
    // @todo use settings.map
    return (
        <div>
            <div className="menu-row">
                <ToggleButton text="showhost"
                    checked={settings.showhost}
                    onToggle={() => SettingsActions.update({ showhost: !settings.showhost })}
                />
                <ToggleButton text="no_upstream_cert"
                    checked={settings.no_upstream_cert}
                    onToggle={() => SettingsActions.update({ no_upstream_cert: !settings.no_upstream_cert })}
                />
                <ToggleButton text="rawtcp"
                    checked={settings.rawtcp}
                    onToggle={() => SettingsActions.update({ rawtcp: !settings.rawtcp })}
                />
                <ToggleButton text="http2"
                    checked={settings.http2}
                    onToggle={() => SettingsActions.update({ http2: !settings.http2 })}
                />
                <ToggleButton text="anticache"
                    checked={settings.anticache}
                    onToggle={() => SettingsActions.update({ anticache: !settings.anticache })}
                />
                <ToggleButton text="anticomp"
                    checked={settings.anticomp}
                    onToggle={() => SettingsActions.update({ anticomp: !settings.anticomp })}
                />
                <ToggleInputButton name="stickyauth" placeholder="Sticky auth filter"
                    checked={!!settings.stickyauth}
                    txt={settings.stickyauth || ''}
                    onToggleChanged={txt => SettingsActions.update({ stickyauth: !settings.stickyauth ? txt : null })}
                />
                <ToggleInputButton name="stickycookie" placeholder="Sticky cookie filter"
                    checked={!!settings.stickycookie}
                    txt={settings.stickycookie || ''}
                    onToggleChanged={txt => SettingsActions.update({ stickycookie: !settings.stickycookie ? txt : null })}
                />
                <ToggleInputButton name="stream" placeholder="stream..."
                    checked={!!settings.stream}
                    txt={settings.stream || ''}
                    inputType="number"
                    onToggleChanged={txt => SettingsActions.update({ stream: !settings.stream ? txt : null })}
                />
            </div>
            <div className="clearfix"/>
        </div>
    )
}
