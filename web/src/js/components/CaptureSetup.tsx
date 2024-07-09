import * as React from "react";
import { useEffect, useRef } from "react";
import { useAppSelector } from "../ducks";
import { ServerInfo } from "../ducks/backendState";
import { formatAddress } from "../utils";
import QRCode from "qrcode";

export default function CaptureSetup() {
    const servers = useAppSelector((state) => state.backendState.servers);

    let configure_action_text;
    if (servers.length === 0) {
        configure_action_text = "";
    } else if (servers.length === 1) {
        configure_action_text =
            "Configure your client to use the following proxy server:";
    } else {
        configure_action_text =
            "Configure your client to use one of the following proxy servers:";
    }

    return (
        <div style={{ padding: "1em 2em" }}>
            <h3>mitmproxy is running.</h3>
            <p>
                No flows have been recorded yet.
                <br />
                {configure_action_text}
            </p>
            <ul className="fa-ul">
                {servers.map((server) => (
                    <li key={server.full_spec}>
                        <ServerDescription {...server} />
                    </li>
                ))}
            </ul>
            {/*
        <p>You can also start additional servers:</p>
        <ul>
            <li>TODO</li>
        </ul>
        */}
        </div>
    );
}

export function ServerDescription({
    description,
    listen_addrs,
    last_exception,
    is_running,
    full_spec,
    wireguard_conf,
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
    let desc, icon;
    if (last_exception) {
        icon = "fa-exclamation text-error";
        desc = (
            <>
                {description} ({full_spec}):
                <br />
                {last_exception}
            </>
        );
    } else if (!is_running) {
        icon = "fa-pause text-warning";
        desc = (
            <>
                {description} ({full_spec})
            </>
        );
    } else {
        icon = "fa-check text-success";
        desc = `${description} listening at ${listen_str}.`;

        if (wireguard_conf) {
            desc = (
                <>
                    {desc}
                    <div className="wireguard-config">
                        <pre>{wireguard_conf}</pre>
                        <canvas ref={qrCode} />
                    </div>
                </>
            );
        }
    }
    return (
        <>
            <i className={`fa fa-li ${icon}`} />
            {desc}
        </>
    );
}
