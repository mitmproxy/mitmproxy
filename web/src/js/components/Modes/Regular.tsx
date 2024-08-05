import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setHost, setPort, toggleRegular } from "../../ducks/modes/regular";
import { Popover } from "./Popover";
import ValueEditor from "../editors/ValueEditor";

export default function Regular() {
    const dispatch = useAppDispatch();

    const {
        active,
        error: ui_error,
        listen_port,
        listen_host,
    } = useAppSelector((state) => state.modes.regular);

    const backend_error = useAppSelector((state) => {
        if (state.backendState.servers) {
            for (const server of state.backendState.servers) {
                if (server.type === "regular") {
                    return server.last_exception;
                }
            }
        }
        return "";
    });

    const handlePortChange = (port: string) => {
        // FIXME: We should eventually cast to Number and validate.
        dispatch(setPort(port as unknown as number));
    };

    const handleHostChange = (host: string) => {
        dispatch(setHost(host));
    };

    return (
        <div>
            <h4 className="mode-title">Explicit HTTP(S) Proxy</h4>
            <p className="mode-description">
                You manually configure your client application or device to use
                an HTTP(S) proxy.
            </p>
            <ModeToggle
                value={active}
                onChange={() => dispatch(toggleRegular())}
            >
                Run HTTP/S Proxy {""}
                <Popover>
                    <div className="mode-popover-item">
                        <p>Listen Host</p>
                        <ValueEditor
                            className="mode-input"
                            content={listen_host || ""}
                            onEditDone={(host) => handleHostChange(host)}
                        />
                    </div>
                    <div className="mode-popover-item">
                        <p>Listen Port</p>
                        <ValueEditor
                            className="mode-input"
                            content={listen_port?.toString() || ""}
                            onEditDone={(port) => handlePortChange(port)}
                        />
                    </div>
                </Popover>
            </ModeToggle>

            {(ui_error || backend_error) && (
                <div className="mode-error text-danger">
                    {ui_error || backend_error}
                </div>
            )}
        </div>
    );
}
