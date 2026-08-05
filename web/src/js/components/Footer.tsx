import * as React from "react";
import { formatSize } from "../utils";
import HideInStatic from "../components/common/HideInStatic";
import { useAppSelector } from "../ducks";
import Badge from "./common/Badge";

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
                <Badge className="footer-badge footer-badge-success">
                    {mode.join(",")}
                </Badge>
            )}
            {intercept && (
                <Badge className="footer-badge footer-badge-success">
                    Intercept: {intercept}
                </Badge>
            )}
            {ssl_insecure && (
                <Badge className="footer-badge footer-badge-danger">
                    ssl_insecure
                </Badge>
            )}
            {showhost && (
                <Badge className="footer-badge footer-badge-success">
                    showhost
                </Badge>
            )}
            {!upstream_cert && (
                <Badge className="footer-badge footer-badge-success">
                    no-upstream-cert
                </Badge>
            )}
            {!rawtcp && (
                <Badge className="footer-badge footer-badge-success">
                    no-raw-tcp
                </Badge>
            )}
            {!http2 && (
                <Badge className="footer-badge footer-badge-success">
                    no-http2
                </Badge>
            )}
            {!websocket && (
                <Badge className="footer-badge footer-badge-success">
                    no-websocket
                </Badge>
            )}
            {anticache && (
                <Badge className="footer-badge footer-badge-success">
                    anticache
                </Badge>
            )}
            {anticomp && (
                <Badge className="footer-badge footer-badge-success">
                    anticomp
                </Badge>
            )}
            {stickyauth && (
                <Badge className="footer-badge footer-badge-success">
                    stickyauth: {stickyauth}
                </Badge>
            )}
            {stickycookie && (
                <Badge className="footer-badge footer-badge-success">
                    stickycookie: {stickycookie}
                </Badge>
            )}
            {stream_large_bodies && (
                <Badge className="footer-badge footer-badge-success">
                    stream: {formatSize(stream_large_bodies)}
                </Badge>
            )}
            {totalFlowsLength > 0 && (
                <Badge className="footer-badge footer-badge-neutral">
                    {selectedFlowsLength} of {totalFlowsLength} flows selected
                </Badge>
            )}
            <div className="footer-meta">
                <HideInStatic>
                    {server && (
                        <Badge
                            className="footer-badge footer-badge-info"
                            title="HTTP Proxy Server Address"
                        >
                            {listen_host || "*"}:{listen_port || 8080}
                        </Badge>
                    )}
                </HideInStatic>
                <Badge
                    className="footer-badge footer-badge-neutral"
                    title="Mitmproxy Version"
                >
                    mitmproxy {version}
                </Badge>
            </div>
        </footer>
    );
}
