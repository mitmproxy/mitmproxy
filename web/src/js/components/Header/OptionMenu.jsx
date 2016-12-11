import React, { PropTypes } from "react"
import { connect } from "react-redux"
import { SettingsToggle, EventlogToggle } from "./MenuToggle"
import DocsLink from "../common/DocsLink"

OptionMenu.title = 'Options'

export default function OptionMenu() {
    return (
        <div>
            <div className="menu-group">
                <div className="menu-content">
                    <SettingsToggle setting="http2">HTTP/2.0</SettingsToggle>
                    <SettingsToggle setting="websocket">WebSockets</SettingsToggle>
                    <SettingsToggle setting="rawtcp">Raw TCP</SettingsToggle>
                </div>
                <div className="menu-legend">Protocol Support</div>
            </div>
            <div className="menu-group">
                <div className="menu-content">
                    <SettingsToggle setting="anticache">
                        Disable Caching <DocsLink resource="features/anticache.html"/>
                    </SettingsToggle>
                    <SettingsToggle setting="anticomp">
                        Disable Compression <i className="fa fa-question-circle"
                                               title="Do not forward Accept-Encoding headers to the server to force an uncompressed response."></i>
                    </SettingsToggle>
                </div>
                <div className="menu-legend">HTTP Options</div>
            </div>
            <div className="menu-group">
                <div className="menu-content">
                    <SettingsToggle setting="showhost">
                        Use Host Header <i className="fa fa-question-circle"
                                           title="Use the Host header to construct URLs for display."></i>
                    </SettingsToggle>
                    <EventlogToggle/>
                </div>
                <div className="menu-legend">View Options</div>
            </div>
            { /*
             <ToggleButton text="no_upstream_cert"
             checked={settings.no_upstream_cert}
             onToggle={() => updateSettings({ no_upstream_cert: !settings.no_upstream_cert })}
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
             <ToggleInputButton name="stream_large_bodies" placeholder="stream..."
             checked={!!settings.stream_large_bodies}
             txt={settings.stream_large_bodies}
             inputType="number"
             onToggleChanged={txt => updateSettings({ stream_large_bodies: !settings.stream_large_bodies ? txt : null })}
             />
             */}
        </div>
    )
}
