import * as React from "react";
import Mode from "./Mode";

export default function HTTPS() {
    return (
        <Mode
            title="Explicit HTTP(S) Proxy"
            description="You manually configure your client application or device to use an HTTP(S) proxy."
        >
            <p>Run HTTP/S Proxy</p>
        </Mode>
    );
}
