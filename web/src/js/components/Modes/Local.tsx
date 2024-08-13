import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setActive, setApplications } from "../../ducks/modes/local";
import ValueEditor from "../editors/ValueEditor";
import { getSpec, LocalState } from "../../modes/local";
import { ServerDescription } from "../CaptureSetup";
import { ServerInfo } from "../../ducks/backendState";

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

    return (
        <div>
            <ModeToggle
                value={server.active}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                Intercept traffic for
                <ValueEditor
                    className="mode-local-input"
                    content={server.applications || ""}
                    onEditDone={(applications) =>
                        dispatch(
                            setApplications({ server, value: applications }),
                        )
                    }
                />
            </ModeToggle>
            <div className="mode-status">
                {error ? (
                    <div className="text-danger">{error}</div>
                ) : (
                    backendState && <ServerDescription {...backendState} />
                )}
            </div>
        </div>
    );
}
