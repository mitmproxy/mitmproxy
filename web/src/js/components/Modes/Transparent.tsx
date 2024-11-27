import * as React from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { getSpec, TransparentState } from "../../modes/transparent";
import { ServerInfo } from "../../ducks/backendState";
import {
    setActive,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/transparent";

import { ModeToggle } from "./ModeToggle";
import { ServerStatus } from "./CaptureSetup";
import ValueEditor from "../editors/ValueEditor";
import { Popover } from "./Popover";

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
                You{" "}
                <a
                    href="https://docs.mitmproxy.org/stable/howto-transparent/"
                    style={{ textDecoration: "underline", color: "inherit" }}
                >
                    configure your routing table
                </a>{" "}
                to send traffic through mitmproxy.
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
                label="Run Transparent Proxy"
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
