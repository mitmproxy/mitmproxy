import * as React from "react";
import { ConnectionState } from "../../ducks/connection";
import { useAppSelector } from "../../ducks";

export default React.memo(function ConnectionIndicator(): React.ReactElement {
    const connState = useAppSelector((state) => state.connection.state);
    const message = useAppSelector((state) => state.connection.message);

    switch (connState) {
        case ConnectionState.INIT:
            return (
                <span className="connection-indicator init">connecting…</span>
            );
        case ConnectionState.FETCHING:
            return (
                <span className="connection-indicator fetching">
                    fetching data…
                </span>
            );
        case ConnectionState.ESTABLISHED:
            return (
                <span className="connection-indicator established">
                    connected
                </span>
            );
        case ConnectionState.ERROR:
            return (
                <span className="connection-indicator error" title={message}>
                    connection lost
                </span>
            );
        case ConnectionState.OFFLINE:
            return (
                <span className="connection-indicator offline">offline</span>
            );
    }
});
