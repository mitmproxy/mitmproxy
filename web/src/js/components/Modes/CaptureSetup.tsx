import * as React from "react";
import { useEffect, useRef } from "react";
import { ServerInfo } from "../../ducks/backendState";
import { formatAddress } from "../../utils";
import QRCode from "qrcode";

export default function CaptureSetup() {
    return (
        <div style={{ padding: "1em 2em" }}>
            <h3>mitmproxy is running.</h3>
            <p>
                No flows have been recorded yet.
                <br />
                To start capturing traffic, please configure your settings in
                the Capture tab.
            </p>
        </div>
    );
}

function ServerDescription({
    description,
    listen_addrs,
    is_running,
    wireguard_conf,
    type,
}: ServerInfo) {
    const qrCode = useRef(null);
    useEffect(() => {
        if (wireguard_conf && qrCode.current)
            QRCode.toCanvas(qrCode.current, wireguard_conf, {
                margin: 0,
                scale: 3,
            });
    }, [wireguard_conf]);

    let listen_str;
    const all_same_port =
        listen_addrs.length === 1 ||
        (listen_addrs.length === 2 &&
            listen_addrs[0][1] === listen_addrs[1][1]);
    const unbound = listen_addrs.every((addr) =>
        ["::", "0.0.0.0"].includes(addr[0]),
    );
    if (all_same_port && unbound) {
        listen_str = formatAddress(["*", listen_addrs[0][1]]);
    } else {
        listen_str = listen_addrs.map(formatAddress).join(" and ");
    }
    description = description[0].toUpperCase() + description.substr(1);
    let desc;
    if (!is_running) {
        desc = (
            <>
                <div className="text-warning">{description} starting...</div>
            </>
        );
    } else {
        desc = (
            <>
                {type === "local" ? (
                    <div className="text-success">{description} is active.</div>
                ) : (
                    <div className="text-success">
                        {description} listening at {listen_str}.
                    </div>
                )}
                {wireguard_conf && (
                    <div className="wireguard-config">
                        <pre>{wireguard_conf}</pre>
                        <canvas ref={qrCode} />
                    </div>
                )}
            </>
        );
    }
    return <div>{desc}</div>;
}

export function ServerStatus({
    error,
    backendState,
}: {
    error?: string;
    backendState?: ServerInfo;
}) {
    return (
        <div className="mode-status">
            {error ? (
                <div className="text-danger">{error}</div>
            ) : (
                backendState && <ServerDescription {...backendState} />
            )}
        </div>
    );
}
