import * as React from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { getSpec, UpstreamState } from "../../modes/upstream";
import { ServerInfo } from "../../ducks/backendState";
import {
    setDestination,
    setActive,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/upstream";
import ValueEditor from "../editors/ValueEditor";
import { ServerStatus } from "./CaptureSetup";
import { ModeToggle } from "./ModeToggle";
import { Popover } from "./Popover";

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
            <h4 className="mode-title">
                Explicit HTTP(S) Proxy (With Upstream Proxy)
            </h4>
            <p className="mode-description">
                All requests are forwarded to a second HTTP(S) proxy server.
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

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label="Run HTTP/S Proxy and forward requests to"
                onChange={() => {
                    dispatch(setActive({ server, value: !server.active }));
                }}
            >
                <ValueEditor
                    className="mode-upstream-input"
                    content={server.destination?.toString() || ""}
                    onEditDone={(value) =>
                        dispatch(setDestination({ server, value }))
                    }
                    placeholder="http://example.com:8080"
                />
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
