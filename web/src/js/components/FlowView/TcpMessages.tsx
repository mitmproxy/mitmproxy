import { TCPFlow } from "../../flow";
import * as React from "react";
import Messages from "./Messages";

export default function TcpMessages({ flow }: { flow: TCPFlow }) {
    return (
        <section className="tcp">
            <Messages flow={flow} messages_meta={flow.messages_meta} />
        </section>
    );
}
TcpMessages.displayName = "Stream Data";
