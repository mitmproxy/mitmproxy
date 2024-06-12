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

            <h3 style={{ marginTop: 30, marginBottom: 10 }}>Recommended</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 15 }}>
                <HTTPS />
                <Local />
                <Wireguard />
                <Reverse />
            </div>
        </div>
    );
}
