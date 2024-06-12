import * as React from "react";
import Mode from "./Mode";

export default function Reverse() {
    return (
        <Mode
            title="Reverse Proxy"
            description="Requests are forwarded to a preconfigured destination."
        >
            <p>Forward DROPDOWN: HTTPS traffic from *:8080 to example.com.</p>
        </Mode>
    );
}
