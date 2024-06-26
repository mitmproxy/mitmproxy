import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { toggleRegular } from "../../ducks/modes/regular";
import ValueEditor from "../editors/ValueEditor";

export default function Regular() {
    const dispatch = useAppDispatch();

    const { active, error, listen_port } = useAppSelector(
        (state) => state.modes.regular,
    );

    React.useEffect(()=> {
        console.log(listen_port)
    },[])

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
                Run HTTP/S Proxy on port{" "}
                <ValueEditor
                    className="mode-regular-input"
                    content={listen_port?.toString() || ""}
                    onEditDone={(port) => console.log(port)}
                />
            </ModeToggle>
            {error && <div className="mode-error text-danger">{error}</div>}
        </div>
    );
}
