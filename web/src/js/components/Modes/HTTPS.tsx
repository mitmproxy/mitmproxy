import * as React from "react";
import Mode, { ModeType } from "./Mode";

export default function HTTPS() {
    return (
        <Mode
            title="Explicit HTTP(S) Proxy"
            description="You manually configure your client application or device to use an HTTP(S) proxy."
            type={ModeType.REGULAR}
        >
            <p>Run HTTP/S Proxy</p>
        </Mode>
    );
}
