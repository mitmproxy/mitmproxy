import * as React from "react";
import { ModeToggle } from "./ModeToggle";

export default function Local() {
    const [active, setActive] = React.useState(false); // temporary

    const [localApps, setLocalApps] = React.useState("");

    return (
        <div>
            <h4 className="mode-title">Local Applications</h4>
            <p className="mode-description">
                Transparently Intercept local application(s).
            </p>
            <ModeToggle value={active} onChange={() => setActive(!active)}>
                Intercept traffic for
                <input
                    type="text"
                    className="mode-local-input"
                    value={localApps}
                    onChange={(e) => setLocalApps(e.target.value)}
                />
            </ModeToggle>
        </div>
    );
}
