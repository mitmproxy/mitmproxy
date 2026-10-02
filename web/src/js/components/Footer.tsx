import * as React from "react";
import { formatSize } from "../utils";
import HideInStatic from "../components/common/HideInStatic";
import { useAppSelector } from "../ducks";
import Badge from "./common/Badge";

type FooterBadgeProps = Omit<
    React.ComponentProps<typeof Badge>,
    "className"
> & {
    variant: "neutral" | "info" | "success" | "danger";
};

function FooterBadge({ variant, ...props }: FooterBadgeProps) {
    return (
        <Badge {...props} className={`footer-badge footer-badge-${variant}`} />
    );
}

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
                <FooterBadge variant="success">{mode.join(",")}</FooterBadge>
            )}
            {intercept && (
                <FooterBadge variant="success">
                    Intercept: {intercept}
                </FooterBadge>
            )}
            {ssl_insecure && (
                <FooterBadge variant="danger">ssl_insecure</FooterBadge>
            )}
            {showhost && <FooterBadge variant="success">showhost</FooterBadge>}
            {!upstream_cert && (
                <FooterBadge variant="success">no-upstream-cert</FooterBadge>
            )}
            {!rawtcp && <FooterBadge variant="success">no-raw-tcp</FooterBadge>}
            {!http2 && <FooterBadge variant="success">no-http2</FooterBadge>}
            {!websocket && (
                <FooterBadge variant="success">no-websocket</FooterBadge>
            )}
            {anticache && (
                <FooterBadge variant="success">anticache</FooterBadge>
            )}
            {anticomp && <FooterBadge variant="success">anticomp</FooterBadge>}
            {stickyauth && (
                <FooterBadge variant="success">
                    stickyauth: {stickyauth}
                </FooterBadge>
            )}
            {stickycookie && (
                <FooterBadge variant="success">
                    stickycookie: {stickycookie}
                </FooterBadge>
            )}
            {stream_large_bodies && (
                <FooterBadge variant="success">
                    stream: {formatSize(stream_large_bodies)}
                </FooterBadge>
            )}
            {totalFlowsLength > 0 && (
                <FooterBadge variant="neutral">
                    {selectedFlowsLength} of {totalFlowsLength} flows selected
                </FooterBadge>
            )}
            <div className="footer-meta">
                <HideInStatic>
                    {server && (
                        <FooterBadge
                            variant="info"
                            title="HTTP Proxy Server Address"
                        >
                            {listen_host || "*"}:{listen_port || 8080}
                        </FooterBadge>
                    )}
                </HideInStatic>
                <FooterBadge variant="neutral" title="Mitmproxy Version">
                    mitmproxy {version}
                </FooterBadge>
            </div>
        </footer>
    );
}
