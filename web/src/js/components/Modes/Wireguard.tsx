import * as React from "react";
import { ModeToggle } from "./ModeToggle";

export default function Wireguard() {
    const [active, setActive] = React.useState(false); // temporary

    return (
        <div>
            <h4 className="mode-title">WireGuard Server</h4>
            <p className="mode-description">
                Start a WireGuard(tm) server and connect an external device for
                transparent proxying.
            </p>
            <ModeToggle value={active} onChange={() => setActive(!active)}>
                Run WireGuard Server
            </ModeToggle>
        </div>
    );
}
