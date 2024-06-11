import * as React from "react";
import ModeToggle from "./Modes/ModeToggle";

export default function Modes() {
    return (
        <div style={{ padding: "1em 2em" }}>
            <h3>Intercept Traffic</h3>
            <p>Configure how you want to intercept traffic with mitmproxy.</p>

            <h4>Recommended</h4>
            <ModeToggle />
        </div>
    );
}
