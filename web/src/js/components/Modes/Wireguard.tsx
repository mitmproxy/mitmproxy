import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { toggleWireguard } from "../../ducks/modes/wireguard";

export default function Wireguard() {
    const dispatch = useAppDispatch();

    const {
        active,
        error: ui_error,
        //listen_host,
        //listen_port,
        //file_path,
    } = useAppSelector((state) => state.modes.wireguard);

    const backend_error = useAppSelector((state) => {
        if (state.backendState.servers) {
            for (const server of state.backendState.servers) {
                if (server.type === "wireguard") {
                    return server.last_exception;
                }
            }
        }
        return "";
    });

    /*
    const handlePortChange = (port: string) => {
        // FIXME: We should eventually cast to Number and validate.
        dispatch(setPort(port as unknown as number));
    };

    const handleHostChange = (host: string) => {
        dispatch(setHost(host));
    };

    const handleFilePathChange = (path: string) => {
        dispatch(setFilePath(path));
    };
    */

    return (
        <div>
            <h4 className="mode-title">WireGuard Server</h4>
            <p className="mode-description">
                Start a WireGuard™ server and connect an external device for
                transparent proxying.
            </p>
            <ModeToggle
                value={active}
                onChange={() => dispatch(toggleWireguard())}
            >
                Run WireGuard Server
                {/* Popover will be added here in the next PR */}
            </ModeToggle>
            {(ui_error || backend_error) && (
                <div className="mode-error text-danger">
                    {ui_error || backend_error}
                </div>
            )}
        </div>
    );
}
