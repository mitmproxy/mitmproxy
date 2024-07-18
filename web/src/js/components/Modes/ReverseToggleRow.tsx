import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import Dropdown, { MenuItem } from "../common/Dropdown";
import ValueEditor from "../editors/ValueEditor";
import { useAppDispatch } from "../../ducks";
import {
    ReverseState,
    setDestination,
    setListenConfig,
    setProtocol,
    toggleReverse,
} from "../../ducks/modes/reverse";
import { ReverseProxyProtocols } from "../../backends/consts";

interface ReverseToggleRowProps {
    modeIndex: number;
    server: ReverseState;
}

export default function ReverseToggleRow({
    modeIndex,
    server,
}: ReverseToggleRowProps) {
    const dispatch = useAppDispatch();

    const protocols = Object.values(ReverseProxyProtocols);

    const inner = (
        <span>
            &nbsp;<b>{server.protocol} </b>
            <span className="caret" />
        </span>
    );

    const handleProtocolChange = (protocol: string) => {
        dispatch(setProtocol(protocol as ReverseProxyProtocols, modeIndex));
    };

    const handleListenHostAndPortChange = (config: string) => {
        const [host, port] = config.split(":");
        // FIXME: We should eventually cast to Number and validate.
        dispatch(setListenConfig(port as unknown as number, host, modeIndex));
    };

    const handleDestinationChange = (host: string) => {
        dispatch(setDestination(host, modeIndex));
    };

    return (
        <div>
            <ModeToggle
                value={server.active}
                onChange={() => {
                    dispatch(toggleReverse(modeIndex));
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
                        server.listen_host && server.listen_port
                            ? `${server.listen_host?.toString()}:${server.listen_port?.toString()}`
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
                    content={server.destination?.toString() || ""}
                    onEditDone={(destination) =>
                        handleDestinationChange(destination)
                    }
                    placeholder="example.com"
                />
            </ModeToggle>
            {server.error && (
                <div className="mode-error text-danger">{server.error}</div>
            )}
        </div>
    );
}
