import * as React from "react";
import HTTPS from "./Modes/HTTPS";
import Local from "./Modes/Local";
import Wireguard from "./Modes/Wireguard";
import Reverse from "./Modes/Reverse";

export default function Modes() {
    return (
        <div style={{ padding: "1em 2em" }}>
            <h2>Intercept Traffic</h2>
            <p>Configure how you want to intercept traffic with mitmproxy.</p>

            <h3 className="modes-subheader">Recommended</h3>
            <div className="modes-container">
                <HTTPS />
                <Local />
                <Wireguard />
                <Reverse />
            </div>
        </div>
    );
}
