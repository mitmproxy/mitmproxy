import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setActive, setSelectedProcesses } from "../../ducks/modes/local";
import { getSpec, LocalState } from "../../modes/local";
import { ServerStatus } from "./CaptureSetup";
import { ServerInfo } from "../../ducks/backendState";
import LocalDropdown from "./LocalDropdown";
import { fetchProcesses } from "../../ducks/processes";

export default function Local() {
    const serverState = useAppSelector((state) => state.modes.local);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <LocalRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">Local Applications</h4>
            <p className="mode-description">
                Transparently Intercept local application(s).
            </p>
            {servers}
        </div>
    );
}

function LocalRow({
    server,
    backendState,
}: {
    server: LocalState;
    backendState?: ServerInfo;
}) {
    const dispatch = useAppDispatch();

    const fetchProcessesError = useAppSelector(
        (state) => state.processes.error,
    );

    const error =
        server.error ||
        backendState?.last_exception ||
        fetchProcessesError ||
        undefined;

    const handleDeletionProcess = (process: string) => {
        const newSelectedProcesses = server.selectedProcesses
            ?.split(", ")
            .filter((p) => p !== process)
            .join(", ");

        dispatch(
            setSelectedProcesses({
                server,
                value: newSelectedProcesses,
            }),
        );
    };

    return (
        <div className="mode-local">
            <ModeToggle
                value={server.active}
                label="Intercept traffic for"
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <div className="processes-container">
                    <div className="selected-processes">
                        {server.selectedProcesses
                            ?.split(", ")
                            .filter((p) => p.trim() !== "")
                            .map((p) => (
                                <div key={p} className="selected-process">
                                    {p}
                                    <i
                                        className="fa fa-times"
                                        aria-hidden="true"
                                        onClick={() => handleDeletionProcess(p)}
                                    ></i>
                                </div>
                            ))}
                    </div>
                    <div className="dropdown-container">
                        <LocalDropdown server={server} />
                        <i
                            className="fa fa-refresh"
                            aria-hidden="true"
                            onClick={() => dispatch(fetchProcesses())}
                        ></i>
                    </div>
                </div>
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
