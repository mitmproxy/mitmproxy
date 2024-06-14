import * as React from "react";
import { ModeToggle } from "./ModeToggle";

export default function Reverse() {
    const [active, setActive] = React.useState(false); // temporary

    return (
        <div>
            <h4 className="mode-title">Reverse Proxy</h4>
            <p className="mode-description">
                Requests are forwarded to a preconfigured destination.
            </p>
            <ModeToggle value={active} onChange={() => setActive(!active)}>
                Forward DROPDOWN: HTTPS traffic from *:8080 to example.com.
            </ModeToggle>
        </div>
    );
}
