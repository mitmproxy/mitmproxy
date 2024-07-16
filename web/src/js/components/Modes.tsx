import * as React from "react";
import Local from "./Modes/Local";
import Regular from "./Modes/Regular";
import Wireguard from "./Modes/Wireguard";
import Reverse from "./Modes/Reverse";

export default function Modes() {
    return (
        <div className="modes">
            <h2>Intercept Traffic</h2>
            <p>Configure how you want to intercept traffic with mitmproxy.</p>

            <h3>Recommended</h3>
            <div className="modes-container">
                <Regular />
                <Local />
                <Wireguard />
                <Reverse />
                <i>Remaining modes are coming soon...</i>
            </div>
        </div>
    );
}
