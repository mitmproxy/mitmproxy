import * as React from "react";
import Mode from "./Mode";

export default function Wireguard() {
    return (
        <Mode
            title="WireGuard Server"
            description="Start a WireGuard(tm) server and connect an external device for transparent proxying."
        >
            <p>Run WireGuard Server</p>
        </Mode>
    );
}
