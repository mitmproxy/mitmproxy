import * as React from "react";
import ReverseToggleRow from "./ReverseToggleRow";
import { ReverseState } from "../../ducks/modes/reverse";
import { ReverseProxyProtocols } from "../../backends/consts";

export default function Reverse() {
    const defaultServerConfig: ReverseState = {
        active: false,
        protocol: ReverseProxyProtocols.HTTPS,
        destination: "",
    };

    // just to see something in the UI, this will be substituted by the redux state
    const [servers, setServers] = React.useState<ReverseState[]>([
        defaultServerConfig,
    ]);

    const handleAddReverseServer = () => {
        setServers([...servers, defaultServerConfig]);
    };

    return (
        <div>
            <h4 className="mode-title">Reverse Proxy</h4>
            <p className="mode-description">
                Requests are forwarded to a preconfigured destination.
            </p>
            <div className="mode-reverse-servers">
                {servers.map((server, index) => (
                    <ReverseToggleRow key={index} />
                ))}
            </div>
            <div
                className="mode-reverse-add-server"
                onClick={handleAddReverseServer}
            >
                <i className="fa fa-plus-square-o" aria-hidden="true"></i>Add
                additional server
            </div>
        </div>
    );
}
