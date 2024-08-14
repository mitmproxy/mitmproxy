import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { getSpec, WireguardState } from "../../modes/wireguard";
import {
    setActive,
    setFilePath,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/wireguard";
import { Popover } from "./Popover";
import ValueEditor from "../editors/ValueEditor";

export default function Wireguard() {
    const serverState = useAppSelector((state) => state.modes.wireguard);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        const error =
            server.error ||
            backendState[getSpec(server)]?.last_exception ||
            undefined;
        return (
            <WireGuardRow key={server.ui_id} server={server} error={error} />
        );
    });

    return (
        <div>
            <h4 className="mode-title">WireGuard Server</h4>
            <p className="mode-description">
                Start a WireGuard™ server and connect an external device for
                transparent proxying.
            </p>
            {servers}
        </div>
    );
}

function WireGuardRow({
    server,
    error,
}: {
    server: WireguardState;
    error?: string;
}) {
    const dispatch = useAppDispatch();

    return (
        <div>
            <ModeToggle
                value={server.active}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                Run WireGuard Server
                <Popover>
                    <p>Listen Host</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        placeholder="(all interfaces)"
                        onEditDone={(host) =>
                            dispatch(setListenHost({ server, value: host }))
                        }
                    />
                    <p>Listen Port</p>
                    <ValueEditor
                        className="mode-input"
                        content={
                            server.listen_port
                                ? server.listen_port.toString()
                                : ""
                        }
                        placeholder="51820"
                        onEditDone={(port) =>
                            dispatch(
                                setListenPort({
                                    server,
                                    value: parseInt(port),
                                }),
                            )
                        }
                    />
                    <p>Configuration File</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.file_path || ""}
                        placeholder="~/.mitmproxy/wireguard.conf"
                        onEditDone={(path) =>
                            dispatch(setFilePath({ server, value: path }))
                        }
                    />
                </Popover>
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
