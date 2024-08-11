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

export default function Regular() {
    const serverState = useAppSelector((state) => state.modes.regular);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        const error =
            server.error ||
            backendState[getSpec(server)]?.last_exception ||
            undefined;
        return <RegularRow key={server.ui_id} server={server} error={error} />;
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
    error,
}: {
    server: RegularState;
    error?: string;
}) {
    const dispatch = useAppDispatch();

    server.listen_host && console.warn("TODO: implement listen_host");

    return (
        <div>
            <ModeToggle
                value={server.active}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                Run HTTP/S Proxy
                <Popover mode="regular">
                    <div className="mode-popover-item">
                        <p>Listen Host</p>
                        <ValueEditor
                            className="mode-input"
                            content={server.listen_host || ""}
                            onEditDone={(host) =>
                                dispatch(setListenHost({ server, value: host }))
                            }
                        />
                    </div>
                    <div className="mode-popover-item">
                        <p>Listen Port</p>
                        <ValueEditor
                            className="mode-input"
                            content={
                                server.listen_port
                                    ? server.listen_port.toString()
                                    : ""
                            }
                            onEditDone={(port) =>
                                dispatch(
                                    setListenPort({
                                        server,
                                        value: parseInt(port),
                                    }),
                                )
                            }
                        />
                    </div>
                </Popover>
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
