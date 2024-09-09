import * as React from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { ServerInfo } from "../../ducks/backendState";
import ValueEditor from "../editors/ValueEditor";
import { ServerStatus } from "./CaptureSetup";
import { ModeToggle } from "./ModeToggle";
import { Popover } from "./Popover";
import { setActive, setListenHost, setListenPort } from "../../ducks/modes/dns";
import { DnsState, getSpec } from "../../modes/dns";

export default function Dns() {
    const serverState = useAppSelector((state) => state.modes.dns);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <DnsRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">DNS Server</h4>
            <p className="mode-description">
                A recursive DNS resolver using the host&apos;s DNS
                configuration.
            </p>
            {servers}
        </div>
    );
}

function DnsRow({
    server,
    backendState,
}: {
    server: DnsState;
    backendState?: ServerInfo;
}) {
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label="Run DNS Server"
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <Popover iconClass="fa fa-cog">
                    <h4>Advanced Configuration</h4>
                    <p>Listen Host</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
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
                        placeholder="8080"
                        onEditDone={(port) =>
                            dispatch(
                                setListenPort({
                                    server,
                                    value: parseInt(port),
                                }),
                            )
                        }
                    />
                </Popover>
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
