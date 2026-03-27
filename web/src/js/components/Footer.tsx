import * as React from "react";
import { formatSize } from "../utils";
import HideInStatic from "../components/common/HideInStatic";
import { useAppSelector } from "../ducks";

export default function Footer() {
    const version = useAppSelector((state) => state.backendState.version);
    const {
        mode,
        intercept,
        showhost,
        upstream_cert,
        rawtcp,
        http2,
        websocket,
        anticache,
        anticomp,
        stickyauth,
        stickycookie,
        stream_large_bodies,
        listen_host,
        listen_port,
        server,
        ssl_insecure,
    } = useAppSelector((state) => state.options);

    const selectedFlowsLength = useAppSelector(
        (state) => state.flows.selected.length,
    );
    const totalFlowsLength = useAppSelector((state) => state.flows.list.length);

    return (
        <footer>
            {mode && (mode.length !== 1 || mode[0] !== "regular") && (
                <span className="m-label m-label-success">{mode.join(",")}</span>
            )}
            {intercept && (
                <span className="m-label m-label-success">
                    Intercept: {intercept}
                </span>
            )}
            {ssl_insecure && (
                <span className="m-label m-label-danger">ssl_insecure</span>
            )}
            {showhost && <span className="m-label m-label-success">showhost</span>}
            {!upstream_cert && (
                <span className="m-label m-label-success">no-upstream-cert</span>
            )}
            {!rawtcp && <span className="m-label m-label-success">no-raw-tcp</span>}
            {!http2 && <span className="m-label m-label-success">no-http2</span>}
            {!websocket && (
                <span className="m-label m-label-success">no-websocket</span>
            )}
            {anticache && (
                <span className="m-label m-label-success">anticache</span>
            )}
            {anticomp && <span className="m-label m-label-success">anticomp</span>}
            {stickyauth && (
                <span className="m-label m-label-success">
                    stickyauth: {stickyauth}
                </span>
            )}
            {stickycookie && (
                <span className="m-label m-label-success">
                    stickycookie: {stickycookie}
                </span>
            )}
            {stream_large_bodies && (
                <span className="m-label m-label-success">
                    stream: {formatSize(stream_large_bodies)}
                </span>
            )}
            {totalFlowsLength > 0 && (
                <span className="m-label m-label-default">
                    {selectedFlowsLength} of {totalFlowsLength} flows selected
                </span>
            )}
            <div className="u-float-right">
                <HideInStatic>
                    {server && (
                        <span
                            className="m-label m-label-primary"
                            title="HTTP Proxy Server Address"
                        >
                            {listen_host || "*"}:{listen_port || 8080}
                        </span>
                    )}
                </HideInStatic>
                <span className="m-label m-label-default" title="Mitmproxy Version">
                    mitmproxy {version}
                </span>
            </div>
        </footer>
    );
}
