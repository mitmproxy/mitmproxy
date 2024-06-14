import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { toggleRegular } from "../../ducks/modes/regular";

export default function Regular() {
    const dispatch = useAppDispatch(),
        active = useAppSelector((state) => state.modes.regular.active),
        error = useAppSelector((state) => state.modes.regular.error);

    return (
        <div>
            <h4 className="mode-title">Explicit HTTP(S) Proxy</h4>
            <p className="mode-description">
                You manually configure your client application or device to use
                an HTTP(S) proxy.
            </p>
            <ModeToggle
                value={active}
                onChange={() => dispatch(toggleRegular())}
            >
                Run HTTP/S Proxy
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
