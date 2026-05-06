import React from "react";
import type { UDPFlow } from "../../flow";
import Messages from "./Messages";

export default function UdpMessages({ flow }: { flow: UDPFlow }) {
    return (
        <section className="udp">
            <Messages flow={flow} messages_meta={flow.messages_meta} />
        </section>
    );
}
UdpMessages.displayName = "Datagrams";
