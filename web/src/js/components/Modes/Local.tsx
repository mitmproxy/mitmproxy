import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setActive, setApplications } from "../../ducks/modes/local";
import ValueEditor from "../editors/ValueEditor";
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

    return (
        <div className="mode-local">
            <ModeToggle
                value={server.active}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                Intercept traffic for
                <LocalDropdown />
                {/*<ValueEditor
                    className="mode-local-input"
                    content={server.applications || ""}
                    placeholder="curl"
                    onEditDone={(applications) =>
                        dispatch(
                            setApplications({ server, value: applications }),
                        )
                    }
                />*/}
                <i className="fa fa-refresh" aria-hidden="true"></i>
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
