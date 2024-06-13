import * as React from "react";
import Mode, { ModeType } from "./Mode";

export default function Reverse() {
    return (
        <Mode
            title="Reverse Proxy"
            description="Requests are forwarded to a preconfigured destination."
            type={ModeType.REVERSE}
        >
            <p>Forward DROPDOWN: HTTPS traffic from *:8080 to example.com.</p>
        </Mode>
    );
}
