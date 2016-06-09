import React from 'react'
import { formatSize } from '../utils.js'
import { SettingsState } from './common.js'

Footer.propTypes = {
    settings: React.PropTypes.object.isRequired,
}

export default function Footer({ settings }) {
    return (
        <footer>
            {settings.mode && settings.mode != "regular" && (
                <span className="label label-success">{settings.mode} mode</span>
            )}
            {settings.intercept && (
                <span className="label label-success">Intercept: {settings.intercept}</span>
            )}
            {settings.showhost && (
                <span className="label label-success">showhost</span>
            )}
            {settings.no_upstream_cert && (
                <span className="label label-success">no-upstream-cert</span>
            )}
            {settings.rawtcp && (
                <span className="label label-success">raw-tcp</span>
            )}
            {!settings.http2 && (
                <span className="label label-success">no-http2</span>
            )}
            {settings.anticache && (
                <span className="label label-success">anticache</span>
            )}
            {settings.anticomp && (
                <span className="label label-success">anticomp</span>
            )}
            {settings.stickyauth && (
                <span className="label label-success">stickyauth: {settings.stickyauth}</span>
            )}
            {settings.stickycookie && (
                <span className="label label-success">stickycookie: {settings.stickycookie}</span>
            )}
            {settings.stream && (
                <span className="label label-success">stream: {formatSize(settings.stream)}</span>
            )}
        </footer>
    )
}
