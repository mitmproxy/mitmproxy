import * as React from "react";
import { ModeToggle } from "./ModeToggle";

export default function Regular() {
    //const dispatch = useAppDispatch(),
    //active = useAppSelector((state) => state.modes.regular.active);

    const [active, setActive] = React.useState(false); // temporary
    return (
        <div>
            <h4 className="mode-title">Explicit HTTP(S) Proxy</h4>
            <p className="mode-description">
                You manually configure your client application or device to use
                an HTTP(S) proxy.
            </p>
            <ModeToggle value={active} onChange={() => setActive(!active)}>
                Run HTTP/S Proxy
            </ModeToggle>
        </div>
    );
}
