import React from "react";
import {SettingsState} from "./common.js";

Footer.propTypes = {
    settings: React.PropTypes.object.isRequired,
};

export default function Footer({ settings }) {
    const {mode, intercept} = settings;
    return (
        <footer>
            {mode && mode != "regular" && (
                <span className="label label-success">{mode} mode</span>
            )}
            {intercept && (
                <span className="label label-success">Intercept: {intercept}</span>
            )}
        </footer>
    );
}
