import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    fetchProcesses,
    setActive,
    setSelectedApplications,
} from "../../ducks/modes/local";
import { getSpec, LocalState } from "../../modes/local";
import { ServerStatus } from "./CaptureSetup";
import { ServerInfo } from "../../ducks/backendState";
import LocalDropdown from "./LocalDropdown";

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

    const error = server.error || backendState?.last_exception || undefined;

    const handleDeletionApplication = (application: string) => {
        const newSelectedApplications = server.selectedApplications
            ?.split(", ")
            .filter((app) => app !== application)
            .join(", ");

        dispatch(
            setSelectedApplications({
                server,
                value: newSelectedApplications,
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
                Intercept traffic for
                <div className="applications-container">
                    <div className="selected-applications">
                        {server.selectedApplications
                            ?.split(", ")
                            .filter((app) => app.trim() !== "")
                            .map((app) => (
                                <div key={app} className="selected-application">
                                    {app}
                                    <i
                                        className="fa fa-times"
                                        aria-hidden="true"
                                        onClick={() =>
                                            handleDeletionApplication(app)
                                        }
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
