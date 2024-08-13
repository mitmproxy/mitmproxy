import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { getSpec, WireguardState } from "../../modes/wireguard";
import { setActive } from "../../ducks/modes/wireguard";
import { ServerDescription } from "../CaptureSetup";
import { ServerInfo } from "../../ducks/backendState";

export default function Wireguard() {
    const serverState = useAppSelector((state) => state.modes.wireguard);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <WireGuardRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
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
    backendState,
}: {
    server: WireguardState;
    backendState?: ServerInfo;
}) {
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                Run WireGuard Server
            </ModeToggle>
            <div className="mode-status">
                {error ? (
                    <div className="text-danger">{error}</div>
                ) : (
                    backendState && <ServerDescription {...backendState} />
                )}
            </div>
        </div>
    );
}
