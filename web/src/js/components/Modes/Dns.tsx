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
            <h4 className="mode-title">Dns Proxy</h4>
            <p className="mode-description">
                This mode will listen for incoming DNS queries and use the
                resolve capabilities of your operation system to return an
                answer.
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
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                Run DNS Server
                <Popover>
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
