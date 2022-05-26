import * as React from 'react'
import {formatSize} from '../utils'
import HideInStatic from '../components/common/HideInStatic'
import {useAppSelector} from "../ducks";

export default function Footer() {
    const version = useAppSelector(state => state.conf.version);
    let {
        mode, intercept, showhost, upstream_cert, rawtcp, dns_server, http2, websocket, anticache, anticomp,
        stickyauth, stickycookie, stream_large_bodies, listen_host, listen_port, server, ssl_insecure
    } = useAppSelector(state => state.options);

    return (
        <footer>
            {mode && mode !== "regular" && (
                <span className="label label-success">{mode} mode</span>
            )}
            {intercept && (
                <span className="label label-success">Intercept: {intercept}</span>
            )}
            {ssl_insecure && (
                <span className="label label-danger">ssl_insecure</span>
            )}
            {showhost && (
                <span className="label label-success">showhost</span>
            )}
            {!upstream_cert && (
                <span className="label label-success">no-upstream-cert</span>
            )}
            {!rawtcp && (
                <span className="label label-success">no-raw-tcp</span>
            )}
            {dns_server && (
                <span className="label label-success">dns-server</span>
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
                        {listen_host || "*"}:{listen_port}
                    </span>)
                    }
                </HideInStatic>
                <span className="label label-default" title="Mitmproxy Version">
            mitmproxy {version}
            </span>
            </div>
        </footer>
    )
}
