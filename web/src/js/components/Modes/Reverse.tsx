import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import Dropdown, { MenuItem } from "../common/Dropdown";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    setHost,
    setListenConfig,
    setProtocol,
    toggleReverse,
} from "../../ducks/modes/reverse";
import ValueEditor from "../editors/ValueEditor";

export default function Reverse() {
    const dispatch = useAppDispatch();

    const { active, protocol, error, listen_port, listen_host, host } =
        useAppSelector((state) => state.modes.reverse);

    const protocols = [
        "http",
        "https",
        "dns",
        "http3",
        "quic",
        "tcp",
        "tls",
        "udp",
        "dtls",
    ];

    let inner = (
        <span>
            &nbsp;<b>{protocol === "" ? "Select protocol" : protocol} </b>
            <span className="caret" />
        </span>
    );

    const handleProtocolChange = (protocol: string) => {
        dispatch(setProtocol(protocol));
    };

    const handleListenHostAndPortChange = (config: string) => {
        const [host, port] = config.split(":");
        // FIXME: We should eventually cast to Number and validate.
        dispatch(setListenConfig(port as unknown as number, host));
    };

    const handleHostChange = (host: string) => {
        dispatch(setHost(host));
    };

    return (
        <div>
            <h4 className="mode-title">Reverse Proxy</h4>
            <p className="mode-description">
                Requests are forwarded to a preconfigured destination.
            </p>
            <ModeToggle
                value={active}
                onChange={() => {
                    if (protocol !== "") {
                        dispatch(toggleReverse());
                    }
                }}
            >
                Forward
                <Dropdown
                    text={inner}
                    className="btn btn-default btn-xs mode-reverse-dropdown"
                    options={{ placement: "bottom" }}
                >
                    {protocols.map((prot) => (
                        <MenuItem
                            key={prot}
                            onClick={() => handleProtocolChange(prot)}
                        >
                            {prot}
                        </MenuItem>
                    ))}
                </Dropdown>{" "}
                traffic from{" "}
                <ValueEditor
                    className="mode-reverse-input"
                    content={
                        listen_host && listen_port
                            ? `${listen_host?.toString()}:${listen_port?.toString()}`
                            : ""
                    }
                    onEditDone={(config) =>
                        handleListenHostAndPortChange(config)
                    }
                    placeholder="*:8080"
                />{" "}
                to{" "}
                <ValueEditor
                    className="mode-reverse-input"
                    content={host?.toString() || ""}
                    onEditDone={(host) => handleHostChange(host)}
                    placeholder="example.com"
                />
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
