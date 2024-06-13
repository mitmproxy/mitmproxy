import * as React from 'react';
import Mode, { ModeType } from './Mode';

export default function Wireguard() {
    return (
        <Mode
            title="WireGuard Server"
            description="Start a WireGuard(tm) server and connect an external device for transparent proxying."
            type={ModeType.WIREGUARD}
        >
            <p>Run WireGuard Server</p>
        </Mode>
    );
}
