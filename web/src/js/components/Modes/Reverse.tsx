import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import Dropdown, { MenuItem } from "../common/Dropdown";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setPort, setProtocol, toggleReverse } from "../../ducks/modes/reverse";
import ValueEditor from "../editors/ValueEditor";

export default function Reverse() {
    const dispatch = useAppDispatch();

    const { active, protocol, error, listen_port } = useAppSelector(
        (state) => state.modes.reverse,
    );

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

    const handlePortChange = (port: string) => {
        // FIXME: We should eventually cast to Number and validate.
        dispatch(setPort(port as unknown as number));
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
                    content={listen_port?.toString() || ""}
                    onEditDone={(port) => handlePortChange(port)}
                    placeholder="port"
                />
                {" "}
                to example.com
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
