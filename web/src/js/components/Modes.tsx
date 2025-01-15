import * as React from "react";
import Local from "./Modes/Local";
import Regular from "./Modes/Regular";
import Wireguard from "./Modes/Wireguard";
import Reverse from "./Modes/Reverse";
import { useAppSelector } from "../ducks";
import Transparent from "./Modes/Transparent";
import Socks from "./Modes/Socks";
import Upstream from "./Modes/Upstream";
import Dns from "./Modes/Dns";
import MissingMode from "./Modes/MissingMode";

export default function Modes() {
    const { platform, localModeUnavailable } = useAppSelector(
        (state) => state.backendState,
    );

    return (
        <div className="modes">
            <h2>Intercept Traffic</h2>
            <p>Configure how you want to intercept traffic with mitmproxy.</p>

            <div className="modes-category green-left-border">
                <h3>Recommended</h3>
                <div className="modes-container">
                    <Regular />
                    {localModeUnavailable !== null ? (
                        <MissingMode
                            title="Local Redirect Mode"
                            description={localModeUnavailable}
                        />
                    ) : (
                        <Local />
                    )}
                    <Wireguard />
                    <Reverse />
                </div>
            </div>
            <div className="modes-category gray-left-border">
                <h3>Advanced</h3>
                <div className="modes-container">
                    <Socks />
                    <Upstream />
                    <Dns />
                    {!platform.startsWith("win32") ? (
                        <Transparent />
                    ) : (
                        <MissingMode
                            title="Transparent Proxy"
                            description="This mode is only supported on Linux and MacOS."
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
