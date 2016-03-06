import React from "react";
import {SettingsState} from "./common.js";

Footer.propTypes = {
    settings: React.PropTypes.object.isRequired,
};

export default function Footer({ settings }) {
    const mode = settings.mode;
    const intercept = settings.intercept;
    return (
        <footer>
            {mode && mode != "regular" ? <span className="label label-success">{mode} mode</span> : null}
            &nbsp;
            {intercept ? <span className="label label-success">Intercept: {intercept}</span> : null}
        </footer>
    );
}
