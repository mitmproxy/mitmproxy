import * as React from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { getSpec, TransparentState } from "../../modes/transparent";
import { ServerInfo } from "../../ducks/backendState";
import { setActive } from "../../ducks/modes/transparent";

import { ModeToggle } from "./ModeToggle";

export default function Transparent() {
    const serverState = useAppSelector((state) => state.modes.transparent);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <TransparentRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">Transparent Proxy</h4>
            <p className="mode-description">
                A transparent proxy routes traffic at the network layer without
                client configuration.
            </p>

            {servers}
        </div>
    );
}

function TransparentRow({
    server,
    backendState,
}: {
    server: TransparentState;
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
                Run Transparent Proxy
                {/** Add here popover to set listen_host and listen_port */}
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
