import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { formatSize } from '../utils.js'
import HideInStatic from '../components/common/HideInStatic'

Footer.propTypes = {
    settings: PropTypes.object.isRequired,
}

function Footer({ settings }) {
    let {mode, intercept, showhost, no_upstream_cert, rawtcp, http2, websocket, anticache, anticomp,
            stickyauth, stickycookie, stream_large_bodies, listen_host, listen_port, version, server} = settings;
    return (
        <footer>
            {mode && mode !== "regular" && (
                <span className="label label-success">{mode} mode</span>
            )}
            {intercept && (
                <span className="label label-success">Intercept: {intercept}</span>
            )}
            {showhost && (
                <span className="label label-success">showhost</span>
            )}
            {no_upstream_cert && (
                <span className="label label-success">no-upstream-cert</span>
            )}
            {!rawtcp && (
                <span className="label label-success">no-raw-tcp</span>
            )}
            {!http2 && (
                <span className="label label-success">no-http2</span>
            )}
            {!websocket && (
                <span className="label label-success">no-websocket</span>
            )}
            {anticache && (
                <span className="label label-success">anticache</span>
            )}
            {anticomp && (
                <span className="label label-success">anticomp</span>
            )}
            {stickyauth && (
                <span className="label label-success">stickyauth: {stickyauth}</span>
            )}
            {stickycookie && (
                <span className="label label-success">stickycookie: {stickycookie}</span>
            )}
            {stream_large_bodies && (
                <span className="label label-success">stream: {formatSize(stream_large_bodies)}</span>
            )}
            <div className="pull-right">
                <HideInStatic>
                {
                    server && (
                    <span className="label label-primary" title="HTTP Proxy Server Address">
                        {listen_host||"*"}:{listen_port}
                    </span>)
                }
                </HideInStatic>
            <span className="label label-info" title="Mitmproxy Version">
            v{version}
            </span>
            </div>
        </footer>
    )
}

export default connect(
    state => ({
        settings: state.settings,
    })
)(Footer)
