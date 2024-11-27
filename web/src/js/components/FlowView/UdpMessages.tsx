import { UDPFlow } from "../../flow";
import * as React from "react";
import Messages from "./Messages";

export default function UdpMessages({ flow }: { flow: UDPFlow }) {
    return (
        <section className="udp">
            <Messages flow={flow} messages_meta={flow.messages_meta} />
        </section>
    );
}
UdpMessages.displayName = "Datagrams";
