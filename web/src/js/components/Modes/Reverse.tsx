import * as React from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    addServer,
    removeServer,
    setActive,
    setDestination,
    setListenHost,
    setListenPort,
    setProtocol,
} from "../../ducks/modes/reverse";
import { getSpec, ReverseState } from "../../modes/reverse";
import { ReverseProxyProtocols } from "../../backends/consts";
import { ServerInfo } from "../../ducks/backendState";
import ValueEditor from "../editors/ValueEditor";
import { ServerStatus } from "./CaptureSetup";
import { ModeToggle } from "./ModeToggle";
import { Popover } from "./Popover";

interface ReverseToggleRowProps {
    removable: boolean;
    server: ReverseState;
    backendState?: ServerInfo;
}

export default function Reverse() {
    const dispatch = useAppDispatch();

    const servers = useAppSelector((state) => state.modes.reverse);
    const backendState = useAppSelector((state) => state.backendState.servers);

    return (
        <div>
            <h4 className="mode-title">Reverse Proxy</h4>
            <p className="mode-description">
                Requests are forwarded to a preconfigured destination.
            </p>
            <div className="mode-reverse-servers">
                {servers.map((server, i) => (
                    <ReverseToggleRow
                        key={server.ui_id}
                        removable={i > 0}
                        server={server}
                        backendState={backendState[getSpec(server)]}
                    />
                ))}
                <div
                    className="mode-reverse-add-server"
                    onClick={() => dispatch(addServer())}
                >
                    <i className="fa fa-plus-square-o" aria-hidden="true"></i>
                    Add additional server
                </div>
            </div>
        </div>
    );
}

function ReverseToggleRow({
    removable,
    server,
    backendState,
}: ReverseToggleRowProps) {
    const dispatch = useAppDispatch();

    const protocols = Object.values(ReverseProxyProtocols);

    const deleteServer = async () => {
        if (server.active) {
            await dispatch(setActive({ server, value: false })).unwrap();
        }
        await dispatch(removeServer(server));
    };

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label="Forward"
                onChange={() => {
                    dispatch(setActive({ server, value: !server.active }));
                }}
            >
                <select
                    name="protocols"
                    className="mode-reverse-dropdown"
                    value={server.protocol}
                    onChange={(e) => {
                        dispatch(
                            setProtocol({
                                server,
                                value: e.target.value as ReverseProxyProtocols,
                            }),
                        );
                    }}
                >
                    {protocols.map((prot) => (
                        <option key={prot} value={prot}>
                            {prot}
                        </option>
                    ))}
                </select>
                traffic to
                <ValueEditor
                    className="mode-reverse-input"
                    content={server.destination?.toString() || ""}
                    onEditDone={(value) =>
                        dispatch(setDestination({ server, value }))
                    }
                    placeholder="example.com"
                />
                <Popover iconClass="fa fa-cog">
                    <h4>Advanced Configuration</h4>
                    <p>Listen Host</p>
                    <ValueEditor
                        className="mode-reverse-input"
                        content={server.listen_host || ""}
                        onEditDone={(value) =>
                            dispatch(setListenHost({ server, value }))
                        }
                        placeholder="*"
                    />
                    <p>Listen Port</p>
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
                    />
                </Popover>
                {removable && (
                    <i
                        className="fa fa-fw fa-trash fa-lg"
                        aria-hidden="true"
                        onClick={deleteServer}
                    ></i>
                )}
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
