import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { toggleWireguard } from "../../ducks/modes/wireguard";

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
                Run WireGuard Server
            </ModeToggle>
            {(ui_error || backend_error) && (
                <div className="mode-error text-danger">
                    {ui_error || backend_error}
                </div>
            )}
        </div>
    );
}
