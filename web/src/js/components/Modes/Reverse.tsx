import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import Dropdown, { MenuItem } from "../common/Dropdown";

export default function Reverse() {
    const [active, setActive] = React.useState(false); // temporary

    const [protocol, setProtocol] = React.useState("");

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
            &nbsp;<b>{protocol === "" ? "Select protocol" : protocol}{" "}</b>
            <span className="caret" />
        </span>
    );

    return (
        <div>
            <h4 className="mode-title">Reverse Proxy</h4>
            <p className="mode-description">
                Requests are forwarded to a preconfigured destination.
            </p>
            <ModeToggle value={active} onChange={() => setActive(!active)}>
                Forward
                <Dropdown
                    text={inner}
                    className="btn btn-default btn-xs mode-reverse-dropdown"
                    options={{ placement: "bottom" }}
                >
                    {protocols.map((name) => (
                        <MenuItem key={name} onClick={() => setProtocol(name)}>
                            {name}
                        </MenuItem>
                    ))}
                </Dropdown>{" "}
                traffic from *:8080 to example.com.
            </ModeToggle>
        </div>
    );
}
