import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { toggleWireguard } from "../../ducks/modes/wireguard";

export default function Wireguard() {
    const dispatch = useAppDispatch();

    const { active, error } = useAppSelector((state) => state.modes.wireguard);

    return (
        <div>
            <h4 className="mode-title">WireGuard Server</h4>
            <p className="mode-description">
                Start a WireGuard(tm) server and connect an external device for
                transparent proxying.
            </p>
            <ModeToggle
                value={active}
                onChange={() => dispatch(toggleWireguard())}
            >
                Run WireGuard Server
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
