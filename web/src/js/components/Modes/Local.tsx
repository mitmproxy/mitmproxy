import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setApplications, toggleLocal } from "../../ducks/modes/local";
import ValueEditor from "../editors/ValueEditor";

export default function Local() {
    const dispatch = useAppDispatch();

    const {
        active,
        applications,
        error: ui_error,
    } = useAppSelector((state) => state.modes.local);

    const backend_error = useAppSelector((state) => {
        if (state.backendState.servers) {
            for (const server of state.backendState.servers) {
                if (server.type === "local") {
                    return server.last_exception;
                }
            }
        }
        return "";
    });

    const handleListApplicationsChange = (applications: string) => {
        dispatch(setApplications(applications));
    };

    return (
        <div>
            <h4 className="mode-title">Local Applications</h4>
            <p className="mode-description">
                Transparently Intercept local application(s).
            </p>
            <ModeToggle value={active} onChange={() => dispatch(toggleLocal())}>
                Intercept traffic for
                <ValueEditor
                    className="mode-local-input"
                    content={applications || ""}
                    onEditDone={(applications) =>
                        handleListApplicationsChange(applications)
                    }
                />
            </ModeToggle>
            {(ui_error || backend_error) && (
                <div className="mode-error text-danger">
                    {ui_error || backend_error}
                </div>
            )}
        </div>
    );
}
