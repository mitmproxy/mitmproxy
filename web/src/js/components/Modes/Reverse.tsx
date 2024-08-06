import * as React from "react";
import ReverseToggleRow from "./ReverseToggleRow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { addServer } from "../../ducks/modes/reverse";

export default function Reverse() {
    const dispatch = useAppDispatch();

    const servers = useAppSelector((state) => state.modes.reverse);

    return (
        <div>
            <h4 className="mode-title">Reverse Proxy</h4>
            <p className="mode-description">
                Requests are forwarded to a preconfigured destination.
            </p>
            <div className="mode-reverse-servers">
                {servers.map((server) => (
                    <ReverseToggleRow key={server.ui_id} server={server} />
                ))}
            </div>
            <div
                className="mode-reverse-add-server"
                onClick={() => dispatch(addServer())}
            >
                <i className="fa fa-plus-square-o" aria-hidden="true"></i>Add
                additional server
            </div>
        </div>
    );
}
