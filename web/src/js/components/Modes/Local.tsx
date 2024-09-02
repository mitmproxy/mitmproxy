import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setActive } from "../../ducks/modes/local";
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

    const [isRefreshing, setIsRefreshing] = React.useState(false);

    return (
        <div className="mode-local">
            <ModeToggle
                value={server.active}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                Intercept traffic for
                <div className="applications-container">
                    {server.selectedApplications?.length ?? 0 > 0 ? (
                        <div className="selected-applications">
                            {server.selectedApplications
                                ?.split(", ")
                                .filter((app) => app.trim() !== "")
                                .map((app) => (
                                    <div
                                        key={app}
                                        className="selected-application"
                                    >
                                        {app}
                                    </div>
                                ))}
                        </div>
                    ) : (
                        <div className="selected-application">
                            all applications
                        </div>
                    )}
                    <div className="dropdown-container">
                        <LocalDropdown
                            server={server}
                            isRefreshing={isRefreshing}
                        />
                        <i
                            className="fa fa-refresh"
                            aria-hidden="true"
                            onClick={() => setIsRefreshing(!isRefreshing)}
                        ></i>
                    </div>
                </div>
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
