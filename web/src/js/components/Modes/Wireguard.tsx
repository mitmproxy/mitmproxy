import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { toggleWireguard } from "../../ducks/modes/wireguard";
import { Popover } from "./Popover";
import ValueEditor from "../editors/ValueEditor";

export default function Wireguard() {
    const dispatch = useAppDispatch();

    const { active, error: ui_error } = useAppSelector(
        (state) => state.modes.wireguard,
    );

    const backend_error = useAppSelector((state) => {
        if (state.backendState.servers) {
            for (const server of state.backendState.servers) {
                if (server.type === "wireguard") {
                    return server.last_exception;
                }
            }
        }
        return "";
    });

    return (
        <div>
            <h4 className="mode-title">WireGuard Server</h4>
            <p className="mode-description">
                Start a WireGuard™ server and connect an external device for
                transparent proxying.
            </p>
            <ModeToggle
                value={active}
                onChange={() => dispatch(toggleWireguard())}
            >
                Run WireGuard Server {""}
                <Popover>
                    <div className="mode-popover-item">
                        <p>Listen Host</p>
                        <ValueEditor
                            className="mode-input"
                            content={""}
                            onEditDone={(host) => console.log(host)}
                        />
                    </div>
                    <div className="mode-popover-item">
                        <p>Listen Port</p>
                        <ValueEditor
                            className="mode-input"
                            content={""}
                            onEditDone={(port) => console.log(port)}
                        />
                    </div>
                    <div className="mode-popover-item">
                        <p>File Path</p>
                        <ValueEditor
                            className="mode-input"
                            content={""}
                            onEditDone={(port) => console.log(port)}
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
