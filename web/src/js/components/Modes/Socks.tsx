import * as React from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { getSpec, SocksState } from "../../modes/socks";
import { ServerInfo } from "../../ducks/backendState";
import { setActive } from "../../ducks/modes/socks";

import { ModeToggle } from "./ModeToggle";

export default function Socks() {
    const serverState = useAppSelector((state) => state.modes.socks);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <SocksRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">SOCKS Proxy</h4>
            <p className="mode-description">
                You manually configure your client application or device to use
                a SOCKSv5 proxy.
            </p>

            {servers}
        </div>
    );
}

function SocksRow({
    server,
    backendState,
}: {
    server: SocksState;
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
                Run SOCKS Proxy
                {/** Add here popover to set listen_host and listen_port */}
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
