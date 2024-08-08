import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { getSpec, WireguardState } from "../../modes/wireguard";
import { setActive } from "../../ducks/modes/wireguard";

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
            <h4 className="mode-title">Explicit HTTP(S) Proxy</h4>
            <p className="mode-description">
                You manually configure your client application or device to use
                an HTTP(S) proxy.
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
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
