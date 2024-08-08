import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setActive, setApplications } from "../../ducks/modes/local";
import ValueEditor from "../editors/ValueEditor";
import { getSpec, LocalState } from "../../modes/local";

export default function Local() {
    const serverState = useAppSelector((state) => state.modes.local);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        const error =
            server.error ||
            backendState[getSpec(server)]?.last_exception ||
            undefined;
        return <LocalRow key={server.ui_id} server={server} error={error} />;
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

function LocalRow({ server, error }: { server: LocalState; error?: string }) {
    const dispatch = useAppDispatch();

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
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
