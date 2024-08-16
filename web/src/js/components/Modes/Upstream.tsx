import * as React from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    getSpec,
    UpstreamProxyProtocols,
    UpstreamState,
} from "../../modes/upstream";
import { ServerInfo } from "../../ducks/backendState";
import {
    setProtocol,
    setDestination,
    setActive,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/upstream";
import Dropdown, { MenuItem } from "../common/Dropdown";
import ValueEditor from "../editors/ValueEditor";
import { ServerStatus } from "./CaptureSetup";
import { ModeToggle } from "./ModeToggle";

export default function Upstream() {
    const serverState = useAppSelector((state) => state.modes.upstream);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <UpstreamRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">Upstream Proxy</h4>
            <p className="mode-description">
                All requests are unconditionally transferred to an upstream
                proxy of your choice.
            </p>
            {servers}
        </div>
    );
}

function UpstreamRow({
    server,
    backendState,
}: {
    server: UpstreamState;
    backendState?: ServerInfo;
}) {
    const dispatch = useAppDispatch();

    const protocols = Object.values(UpstreamProxyProtocols);

    const inner = (
        <span>
            &nbsp;<b>{server.protocol} </b>
            <span className="caret" />
        </span>
    );

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                onChange={() => {
                    dispatch(setActive({ server, value: !server.active }));
                }}
            >
                Transfer
                <Dropdown
                    text={inner}
                    className="btn btn-default btn-xs mode-reverse-dropdown"
                    options={{ placement: "bottom" }}
                >
                    {protocols.map((prot) => (
                        <MenuItem
                            key={prot}
                            onClick={() =>
                                dispatch(setProtocol({ server, value: prot }))
                            }
                        >
                            {prot}
                        </MenuItem>
                    ))}
                </Dropdown>{" "}
                traffic from{" "}
                <ValueEditor
                    className="mode-reverse-input"
                    content={server.listen_host || ""}
                    onEditDone={(value) =>
                        dispatch(setListenHost({ server, value }))
                    }
                    placeholder="*"
                />
                <ValueEditor
                    className="mode-reverse-input"
                    content={String(server.listen_port || "")}
                    onEditDone={(value) =>
                        dispatch(
                            setListenPort({
                                server,
                                value: value as unknown as number,
                            }),
                        )
                    }
                    placeholder="8080"
                />{" "}
                to{" "}
                <ValueEditor
                    className="mode-reverse-input"
                    content={server.destination?.toString() || ""}
                    onEditDone={(value) =>
                        dispatch(setDestination({ server, value }))
                    }
                    placeholder="example.com"
                />
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
