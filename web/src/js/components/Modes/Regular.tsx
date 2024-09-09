import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    setListenPort,
    setActive,
    setListenHost,
} from "../../ducks/modes/regular";
import ValueEditor from "../editors/ValueEditor";
import { getSpec, RegularState } from "../../modes/regular";
import { Popover } from "./Popover";
import { ServerInfo } from "../../ducks/backendState";
import { ServerStatus } from "./CaptureSetup";

export default function Regular() {
    const serverState = useAppSelector((state) => state.modes.regular);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <RegularRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
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

function RegularRow({
    server,
    backendState,
}: {
    server: RegularState;
    error?: string;
    backendState?: ServerInfo;
}) {
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label="Run HTTP/S Proxy"
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
