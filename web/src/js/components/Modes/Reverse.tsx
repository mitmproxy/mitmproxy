import * as React from "react";
import ReverseToggleRow from "./ReverseToggleRow";

export default function Reverse() {

    const handleAddReverseServer = () => {
        console.log("Add reverse server");
    }

    return (
        <div>
            <h4 className="mode-title">Reverse Proxy</h4>
            <p className="mode-description">
                Requests are forwarded to a preconfigured destination.
            </p>
            <ReverseToggleRow />
            <div className="mode-reverse-add-server" onClick={handleAddReverseServer}>
                <i className="fa fa-plus-square-o" aria-hidden="true"></i>Add
                additional server
            </div>
        </div>
    );
}