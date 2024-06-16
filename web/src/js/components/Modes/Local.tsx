import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { addApplications, toggleLocal } from "../../ducks/modes/local";

export default function Local() {
    const dispatch = useAppDispatch();

    const { active, applications, error } = useAppSelector(
        (state) => state.modes.local
    );

    const [listApplications, setListApplications] = React.useState(
        applications || ""
    );

    const handleListApplicationsChange = (
        e: React.ChangeEvent<HTMLInputElement>
    ) => {
        setListApplications(e.target.value);
        dispatch(addApplications(e.target.value));
    };

    return (
        <div>
            <h4 className="mode-title">Local Applications</h4>
            <p className="mode-description">
                Transparently Intercept local application(s).
            </p>
            <ModeToggle value={active} onChange={() => dispatch(toggleLocal())}>
                Intercept traffic for
                <input
                    type="text"
                    className="mode-local-input"
                    value={listApplications}
                    onChange={(e) => handleListApplicationsChange(e)}
                />
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
