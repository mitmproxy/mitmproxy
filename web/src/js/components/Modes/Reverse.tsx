import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import Dropdown, { MenuItem } from "../common/Dropdown";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { addProtocols, toggleReverse } from "../../ducks/modes/reverse";

export default function Reverse() {
    const dispatch = useAppDispatch();

    const { active, protocols, error } = useAppSelector(
        (state) => state.modes.reverse
    );

    const [protocol, setProtocol] = React.useState(protocols[0].name);

    let inner = (
        <span>
            &nbsp;<b>{protocol} </b>
            <span className="caret" />
        </span>
    );

    const handleProtocolChange = (protocolName: string) => {
        setProtocol(protocolName);
        dispatch(addProtocols(protocolName));
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
                    dispatch(toggleReverse());
                }}
            >
                Forward
                <Dropdown
                    text={inner}
                    className="btn btn-default btn-xs mode-reverse-dropdown"
                    options={{ placement: "bottom" }}
                >
                    {protocols.map((protocol) => (
                        <MenuItem
                            key={protocol.name}
                            onClick={() => handleProtocolChange(protocol.name)}
                        >
                            {protocol.name}
                        </MenuItem>
                    ))}
                </Dropdown>{" "}
                traffic from *:8080 to example.com.
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
