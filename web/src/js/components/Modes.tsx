import * as React from "react";
import Local from "./Modes/Local";
import Regular from "./Modes/Regular";
import Wireguard from "./Modes/Wireguard";
import Reverse from "./Modes/Reverse";
import { useAppSelector } from "../ducks";

export default function Modes() {
    const platform = useAppSelector((state) => state.backendState.platform);
    return (
        <div className="modes">
            <h2>Intercept Traffic</h2>
            <p>Configure how you want to intercept traffic with mitmproxy.</p>

            <h3>Recommended</h3>
            <div className="modes-container">
                <Regular />
                {!platform.startsWith("linux") ? <Local /> : undefined}
                <Wireguard />
                <Reverse />
                <i>Remaining modes are coming soon...</i>
            </div>
        </div>
    );
}
